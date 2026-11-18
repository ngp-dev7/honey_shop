from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

from common.translated import translated


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

    name = translated("name")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = _("category")
        verbose_name_plural = _("categories")

    def __str__(self):
        return self.name


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

    name = translated("name")
    summary = translated("summary")
    description = translated("description")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = _("product")
        verbose_name_plural = _("products")

    def __str__(self):
        return self.name


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
        _("price (Rial)"), validators=[MinValueValidator(1)]
    )
    old_price_rial = models.PositiveBigIntegerField(
        _("old price (Rial)"),
        null=True,
        blank=True,
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
        ]

    def __str__(self):
        return f"{self.product} ({self.sku})"

    @property
    def is_in_stock(self):
        return self.stock > 0
