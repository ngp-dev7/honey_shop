import uuid

from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Exists, F, OuterRef, Q
from django.db.models.functions import Mod
from django.db.models.lookups import Exact
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from common.formatting import RIAL_PER_TOMAN
from common.text import digit_forms, normalize_persian
from common.translated import translated

from .images import process_image, validate_image
from .validators import validate_whole_toman


class CategoryQuerySet(models.QuerySet):
    def visible(self):
        """Active categories that have at least one active product."""
        active_products = Product.objects.filter(
            category=OuterRef("pk"), is_active=True
        )
        return self.filter(is_active=True).filter(Exists(active_products))


class Category(models.Model):
    slug = models.SlugField(
        _("slug"),
        max_length=80,
        unique=True,
        help_text=_("Latin letters, digits and hyphens. Used in the web address."),
    )
    name_fa = models.CharField(_("name (Persian)"), max_length=100)
    name_en = models.CharField(_("name (English)"), max_length=100, blank=True)
    sort_order = models.PositiveSmallIntegerField(_("sort order"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    objects = CategoryQuerySet.as_manager()

    name = translated("name")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = _("category")
        verbose_name_plural = _("categories")

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    MAX_QUERY_LENGTH = 100
    MAX_WORDS = 6
    SEARCH_FIELDS = (
        "name_fa",
        "name_en",
        "summary_fa",
        "summary_en",
        "category__name_fa",
        "category__name_en",
    )

    def visible(self):
        """Products a visitor may see: active, in an active category."""
        return self.filter(is_active=True, category__is_active=True)

    def search(self, query):
        """Every word must match somewhere; Persian typing habits are handled."""
        words = normalize_persian(query or "")[: self.MAX_QUERY_LENGTH].split()
        result = self
        for word in words[: self.MAX_WORDS]:
            condition = Q()
            for form in digit_forms(word):
                for field in self.SEARCH_FIELDS:
                    condition |= Q(**{f"{field}__icontains": form})
            result = result.filter(condition)
        return result


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name=_("category"),
    )
    slug = models.SlugField(
        _("slug"),
        max_length=100,
        unique=True,
        help_text=_("Latin letters, digits and hyphens. Used in the web address."),
    )
    name_fa = models.CharField(_("name (Persian)"), max_length=150)
    name_en = models.CharField(_("name (English)"), max_length=150, blank=True)
    summary_fa = models.CharField(_("summary (Persian)"), max_length=255, blank=True)
    summary_en = models.CharField(_("summary (English)"), max_length=255, blank=True)
    description_fa = models.TextField(_("description (Persian)"), blank=True)
    description_en = models.TextField(_("description (English)"), blank=True)
    sort_order = models.PositiveSmallIntegerField(_("sort order"), default=0)
    is_active = models.BooleanField(_("active"), default=True)
    is_featured = models.BooleanField(_("featured"), default=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    objects = ProductQuerySet.as_manager()

    name = translated("name")
    summary = translated("summary")
    description = translated("description")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = _("product")
        verbose_name_plural = _("products")

    def __str__(self):
        return self.name

    # The helpers below read prefetched data, so a list page does not query
    # the database once per product.
    @property
    def active_variants(self):
        return [v for v in self.variants.all() if v.is_active]

    @property
    def from_variant(self):
        """The cheapest active size, or None."""
        variants = self.active_variants
        return min(variants, key=lambda v: v.price_rial) if variants else None

    @property
    def is_available(self):
        return any(v.is_in_stock for v in self.active_variants)

    @property
    def main_image(self):
        return next(iter(self.images.all()), None)


class Variant(models.Model):
    """One size of a product, for example 500 g. Customers buy variants."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
        verbose_name=_("product"),
    )
    sku = models.CharField(_("stock code (SKU)"), max_length=40, unique=True)
    weight_grams = models.PositiveIntegerField(
        _("weight (grams)"), validators=[MinValueValidator(1)]
    )
    label_fa = models.CharField(_("label (Persian)"), max_length=60, blank=True)
    label_en = models.CharField(_("label (English)"), max_length=60, blank=True)
    price_rial = models.PositiveBigIntegerField(
        _("price (Rial)"),
        validators=[MinValueValidator(1), validate_whole_toman],
    )
    old_price_rial = models.PositiveBigIntegerField(
        _("old price (Rial)"),
        null=True,
        blank=True,
        validators=[validate_whole_toman],
        help_text=_("Optional. Must be higher than the price. Shown as a discount."),
    )
    stock = models.PositiveIntegerField(_("stock"), default=0)
    sort_order = models.PositiveSmallIntegerField(_("sort order"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    label = translated("label")

    class Meta:
        ordering = ["sort_order", "weight_grams"]
        verbose_name = _("variant")
        verbose_name_plural = _("variants")
        constraints = [
            models.CheckConstraint(
                condition=Q(old_price_rial__isnull=True)
                | Q(old_price_rial__gt=F("price_rial")),
                name="variant_old_price_above_price",
            ),
            models.CheckConstraint(
                condition=Q(Exact(Mod("price_rial", RIAL_PER_TOMAN), 0)),
                name="variant_price_whole_toman",
            ),
            models.CheckConstraint(
                condition=Q(old_price_rial__isnull=True)
                | Q(Exact(Mod("old_price_rial", RIAL_PER_TOMAN), 0)),
                name="variant_old_price_whole_toman",
            ),
        ]

    def __str__(self):
        return f"{self.product} ({self.sku})"

    @property
    def is_in_stock(self):
        return self.stock > 0

    @property
    def discount_percent(self):
        """Discount in whole percent, rounded down. 0 when there is none."""
        if not self.old_price_rial or self.old_price_rial <= self.price_rial:
            return 0
        return (self.old_price_rial - self.price_rial) * 100 // self.old_price_rial


def validate_new_image(value):
    """Check fresh uploads only; stored files were already checked and resized."""
    if not value._committed:
        validate_image(value)


def _delete_files(storage, names):
    for name in names:
        storage.delete(name)


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("product"),
    )
    image = models.FileField(
        _("image"),
        upload_to="products/",
        validators=[validate_new_image],
        help_text=_("JPEG, PNG or WebP. It is resized automatically."),
    )
    alt_fa = models.CharField(_("description (Persian)"), max_length=150, blank=True)
    alt_en = models.CharField(_("description (English)"), max_length=150, blank=True)
    sort_order = models.PositiveSmallIntegerField(_("sort order"), default=0)
    # Filled automatically when an image is uploaded.
    width = models.PositiveIntegerField(editable=False, default=0)
    height = models.PositiveIntegerField(editable=False, default=0)
    files = models.JSONField(editable=False, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    alt = translated("alt")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = _("product image")
        verbose_name_plural = _("product images")

    def __str__(self):
        return f"{self.product} #{self.pk}"

    @property
    def sorted_files(self):
        """(width, storage name) pairs, smallest first."""
        return sorted((int(width), name) for width, name in self.files.items())

    @property
    def srcset(self):
        storage = self.image.storage
        return ", ".join(
            f"{storage.url(name)} {width}w" for width, name in self.sorted_files
        )

    @property
    def small_url(self):
        files = self.sorted_files
        return self.image.storage.url(files[0][1]) if files else ""

    def save(self, *args, **kwargs):
        storage = self._meta.get_field("image").storage
        new_names = []
        old_names = []

        if self.image and not self.image._committed:
            if self.pk:
                previous = (
                    ProductImage.objects.filter(pk=self.pk)
                    .values_list("files", flat=True)
                    .first()
                )
                old_names = list((previous or {}).values())

            processed = process_image(self.image)
            stem = uuid.uuid4().hex
            files = {}
            for item in processed:
                name = storage.save(
                    f"products/{stem}-{item.width}.webp", ContentFile(item.data)
                )
                files[str(item.width)] = name
                new_names.append(name)

            largest = processed[-1]
            self.image = files[str(largest.width)]
            self.width = largest.width
            self.height = largest.height
            self.files = files

        try:
            super().save(*args, **kwargs)
        except Exception:
            _delete_files(storage, new_names)
            raise

        if old_names:
            transaction.on_commit(lambda: _delete_files(storage, old_names))


@receiver(post_delete, sender=ProductImage)
def delete_product_image_files(sender, instance, **kwargs):
    names = list(instance.files.values())
    if not names and instance.image:
        names = [instance.image.name]
    storage = instance.image.storage
    transaction.on_commit(lambda: _delete_files(storage, names))


class ProductSpec(models.Model):
    """One row of the specification table, for example "Origin: ..."."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="specs",
        verbose_name=_("product"),
    )
    label_fa = models.CharField(_("label (Persian)"), max_length=100)
    label_en = models.CharField(_("label (English)"), max_length=100, blank=True)
    value_fa = models.CharField(_("value (Persian)"), max_length=200)
    value_en = models.CharField(_("value (English)"), max_length=200, blank=True)
    sort_order = models.PositiveSmallIntegerField(_("sort order"), default=0)

    label = translated("label")
    value = translated("value")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = _("specification")
        verbose_name_plural = _("specifications")

    def __str__(self):
        return f"{self.label}: {self.value}"
