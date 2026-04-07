

document.addEventListener('DOMContentLoaded', function () {

    // Fetch mappings from your API endpoint
    fetch('/sales/api/dropdown-mappings/')
        .then(res => res.json())
        .then(data => {
            window.categoryProductMap = data.categories || {};
            window.productBatchMap = data.batches || {};

            // Initialize all existing rows
            initDropdowns(document);
        })
        .catch(err => {
            console.warn("Dropdown mappings could not be loaded:", err);
            window.categoryProductMap = {};
            window.productBatchMap = {};
        });

    /**
     * Attach change event listeners to category and product selects
     * Works for single form and dynamically added formset rows
     */
    function initDropdowns(container) {
        container.querySelectorAll('select[name*="category"]').forEach(categorySelect => {
            categorySelect.removeEventListener('change', handleCategoryChange);
            categorySelect.addEventListener('change', handleCategoryChange);
        });

        container.querySelectorAll('select[name*="product"]').forEach(productSelect => {
            productSelect.removeEventListener('change', handleProductChange);
            productSelect.addEventListener('change', handleProductChange);
        });
    }

    /** Handle category change: populate product dropdown */
    function handleCategoryChange(e) {
        const categoryId = parseInt(e.target.value);
        const row = e.target.closest('tr, .form-row, .form-group');

        if (!row) return;

        const productSelect = row.querySelector('select[name*="product"]');
        const batchSelect = row.querySelector('select[name*="batch"]');

        if (productSelect) {
            productSelect.innerHTML = '<option value="">-- Select Product --</option>';

            if (!isNaN(categoryId) && window.categoryProductMap[categoryId]) {
                window.categoryProductMap[categoryId].forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p.id;
                    opt.textContent = p.name;
                    productSelect.appendChild(opt);
                });
            }
        }

        if (batchSelect) {
            batchSelect.innerHTML = '<option value="">-- Select Batch --</option>';
        }
    }

    /** Handle product change: populate batch dropdown */
    function handleProductChange(e) {
        const productId = parseInt(e.target.value);
        const row = e.target.closest('tr, .form-row, .form-group');

        if (!row) return;

        const batchSelect = row.querySelector('select[name*="batch"]');

        if (batchSelect) {
            batchSelect.innerHTML = '<option value="">-- Select Batch --</option>';

            if (!isNaN(productId) && window.productBatchMap[productId]) {
                window.productBatchMap[productId].forEach(b => {
                    const opt = document.createElement('option');
                    opt.value = b.id;
                    opt.textContent = `${b.batch_number} (${b.remaining_quantity} units)`;
                    batchSelect.appendChild(opt);
                });
            } else {
                const opt = document.createElement('option');
                opt.disabled = true;
                opt.textContent = 'No batch available';
                batchSelect.appendChild(opt);
            }
        }
    }

    // Observe DOM for dynamically added formset rows
    const observer = new MutationObserver(mutations => {
        mutations.forEach(m => {
            m.addedNodes.forEach(node => {
                if (node.nodeType === 1) initDropdowns(node);
            });
        });
    });

    observer.observe(document.body, { childList: true, subtree: true });

});
