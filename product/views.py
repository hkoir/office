from django.shortcuts import render,redirect,get_object_or_404
from django.contrib import messages
from.forms import AddCategoryForm,AddProductForm

from.models import Category,Product
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import ProgrammingError
from django.contrib.auth.decorators import login_required,permission_required

from purchase.models import Batch
from django.db.models import Q

@login_required
def product_dashboard(request):
    return render(request,'product/product_dashboard.html')

@login_required
def print_unit_labels(request, batch_id):
    batch = get_object_or_404(Batch, id=batch_id)
    total_units = batch.units.count()

    # Default quantity = 1 (to avoid printing all accidentally)
    quantity_to_print = 1
    selected_quantity = 1

    if request.method == "POST":
        qty = request.POST.get("quantity")
        try:
            qty = int(qty)
            if 1 <= qty <= total_units:
                quantity_to_print = qty
                selected_quantity = qty
        except (ValueError, TypeError):
            pass  # ignore invalid input

    # We don’t need to slice actual units; just use a range
    return render(request, "product/unit_labels.html", {
        "batch": batch,
        "quantity_to_print": quantity_to_print,
        "selected_quantity": selected_quantity,
        "max_quantity": total_units,
    })


@login_required
def manage_category(request, id=None):
    query = request.GET.get('q', '').strip()
    categories = Category.objects.all().order_by('-created_at')

    if query:
        categories = categories.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

  
    instance = get_object_or_404(Category, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = AddCategoryForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('product:create_category')

    datas = categories
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'product/manage_category.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_category(request, id):
    instance = get_object_or_404(Category, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('product:create_category')

    messages.warning(request, "Invalid delete request!")
    return redirect('product:create_category')



@login_required
def manage_product(request, id=None):
    query = request.GET.get('q', '').strip()
    products = Product.objects.all().order_by('-created_at')

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(barcode__icontains=query) |
            Q(product_type__icontains=query)
        )
    instance = get_object_or_404(Product, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"
    form = AddProductForm(request.POST or None, request.FILES or None, instance=instance)
    if request.method == 'POST':
        if form.is_valid():
            form_instance = form.save(commit=False)
            form_instance.user = request.user
            form_instance.save()
            messages.success(request, message_text)
            return redirect('product:create_product')
        else:          
            messages.error(request, "Please correct the errors below.")
    datas = products
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'product/manage_product.html', {
        'form': form,          # ← same form (with validation errors)
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_product(request, id):
    instance = get_object_or_404(Product, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('product:create_product')

    messages.warning(request, "Invalid delete request!")
    return redirect('product:create_product')


@login_required
def product_data(request,product_id):
    product_instance = get_object_or_404(Product,id=product_id)
    return render(request,'product/product_data.html',{'product_instance':product_instance})








from django.http import JsonResponse
from purchase.models import Batch

def dropdown_mappings_api(request):  
    category_product_map = {}
    for p in Product.objects.select_related('category').all():
        category_product_map.setdefault(p.category_id, []).append({
            'id': p.id,
            'name': p.name
        })

    product_batch_map = {}
    for b in Batch.objects.select_related('product').all():
        product_batch_map.setdefault(b.product_id, []).append({
            'id': b.id,
            'batch_number': b.batch_number,
            'remaining_quantity': b.remaining_quantity or 0
        })

    return JsonResponse({
        'categories': category_product_map,
        'batches': product_batch_map
    })
