from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render

from .models import Category, Product, ProductQuerySet

PAGE_SIZE = 12


def product_list(request, slug=None):
    categories = list(Category.objects.visible())
    category = None
    if slug is not None:
        category = next((c for c in categories if c.slug == slug), None)
        if category is None:
            raise Http404

    query = request.GET.get("q", "").replace("\x00", "").strip()
    query = query[: ProductQuerySet.MAX_QUERY_LENGTH]

    products = (
        Product.objects.visible()
        .select_related("category")
        .prefetch_related("variants", "images")
    )
    if category is not None:
        products = products.filter(category=category)
    products = products.search(query)

    paginator = Paginator(products, PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "catalog/product_list.html",
        {
            "products": page,
            "count": paginator.count,
            "categories": categories,
            "category": category,
            "query": query,
            # Keep the search when switching category or page.
            "query_suffix": "?" + urlencode({"q": query}) if query else "",
            "qs": urlencode({"q": query}) + "&" if query else "",
        },
    )
