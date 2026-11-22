from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from .models import Category, Product, ProductImage, ProductSpec, Variant


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 1
    fields = (
        "sku",
        "weight_grams",
        "label_fa",
        "label_en",
        "price_rial",
        "old_price_rial",
        "stock",
        "sort_order",
        "is_active",
    )


class ProductImageInline(admin.StackedInline):
    model = ProductImage
    extra = 0
    fields = ("preview", "image", ("alt_fa", "alt_en"), "sort_order")
    readonly_fields = ("preview",)

    @admin.display(description=_("preview"))
    def preview(self, obj):
        if obj.pk and obj.small_url:
            return format_html('<img src="{}" width="120" alt="">', obj.small_url)
        return "-"


class ProductSpecInline(admin.TabularInline):
    model = ProductSpec
    extra = 1
    fields = ("label_fa", "value_fa", "label_en", "value_en", "sort_order")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "sort_order", "is_active", "product_total")
    list_editable = ("sort_order", "is_active")
    prepopulated_fields = {"slug": ("name_en",)}
    fields = ("slug", ("name_fa", "name_en"), "sort_order", "is_active")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(product_total=Count("products"))

    @admin.display(description=_("products"), ordering="product_total")
    def product_total(self, obj):
        return obj.product_total


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail",
        "name",
        "category",
        "is_active",
        "is_featured",
        "stock_summary",
    )
    list_display_links = ("thumbnail", "name")
    list_editable = ("is_active", "is_featured")
    list_filter = ("is_active", "is_featured", "category")
    search_fields = ("name_fa", "name_en", "slug", "variants__sku")
    prepopulated_fields = {"slug": ("name_en",)}
    inlines = [VariantInline, ProductImageInline, ProductSpecInline]
    actions = ["make_active", "make_inactive"]

    fieldsets = (
        (None, {"fields": ("category", "slug", ("name_fa", "name_en"))}),
        (
            _("Descriptions"),
            {
                "fields": (
                    ("summary_fa", "summary_en"),
                    "description_fa",
                    "description_en",
                )
            },
        ),
        (_("Display"), {"fields": ("is_active", "is_featured", "sort_order")}),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("category")
            .prefetch_related("variants", "images")
        )

    @admin.display(description=_("image"))
    def thumbnail(self, obj):
        image = next(iter(obj.images.all()), None)
        if image and image.small_url:
            return format_html('<img src="{}" width="48" alt="">', image.small_url)
        return "-"

    @admin.display(description=_("stock"))
    def stock_summary(self, obj):
        variants = [v for v in obj.variants.all() if v.is_active]
        if not variants:
            return "-"
        total = sum(v.stock for v in variants)
        out_of_stock = sum(1 for v in variants if not v.is_in_stock)
        if not out_of_stock:
            return total
        warning = ngettext(
            "%(count)d variant out of stock",
            "%(count)d variants out of stock",
            out_of_stock,
        ) % {"count": out_of_stock}
        return format_html(
            '{} <strong style="color: var(--error-fg)">({})</strong>', total, warning
        )

    @admin.action(description=_("Activate selected products"))
    def make_active(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            ngettext(
                "%(count)d product activated.",
                "%(count)d products activated.",
                count,
            )
            % {"count": count},
        )

    @admin.action(description=_("Deactivate selected products"))
    def make_inactive(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            ngettext(
                "%(count)d product deactivated.",
                "%(count)d products deactivated.",
                count,
            )
            % {"count": count},
        )
