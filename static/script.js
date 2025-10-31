document.addEventListener('DOMContentLoaded', () => {
    
    const categoryNav = document.getElementById('category-nav');
    const productList = document.getElementById('product-list');
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const paginationControls = document.getElementById('pagination-controls');
    const sortSelect = document.getElementById('sort-select');
    
    // Bỏ `allProducts` đi, vì giờ ta lấy từ backend
    let currentProducts = []; 
    let currentPage = 1;
    const itemsPerPage = 25;
    let currentCategoryId = null;

    // --- THAY ĐỔI: Chỉ lấy danh mục khi tải trang ---
    async function fetchCategories() {
        try {
            // Gọi API /api/categories
            const response = await fetch('/api/categories');
            const categories = await response.json();
            displayCategories(categories);
            
            // Xóa thông báo loading ban đầu
            productList.innerHTML = '<p>Hãy chọn danh mục hoặc tìm kiếm để xem sản phẩm.</p>';
            paginationControls.innerHTML = '';
        } catch (error) {
            console.error('Lỗi khi tải danh mục:', error);
            productList.innerHTML = '<p>Không thể tải danh mục sản phẩm.</p>';
        }
    }

    // Hàm để hiển thị các nút danh mục (Không đổi)
    function displayCategories(categories) {
        categoryNav.innerHTML = '<h2>Danh mục sản phẩm</h2>';
        categories.forEach(category => {
            const button = document.createElement('button');
            button.textContent = category.name;
            button.classList.add('category-button');
            button.dataset.categoryId = category.id;
            button.onclick = (event) => {
                handleCategoryClick(event.currentTarget, category.id);
            };
            categoryNav.appendChild(button);
        });
    }

    // --- HÀM MỚI: Xử lý khi bấm vào danh mục ---
    function handleCategoryClick(clickedButton, categoryId) {
        currentCategoryId = categoryId;
        searchInput.value = '';

        document.querySelectorAll('.category-button').forEach(btn => btn.classList.remove('active'));
        if (clickedButton) clickedButton.classList.add('active');

        filterAndDisplayProducts();
    }

    // --- HÀM MỚI: Xử lý khi bấm nút tìm kiếm ---
    function handleSearchClick() {
        // Bỏ chọn category ID khi tìm kiếm
        currentCategoryId = null; 
        document.querySelectorAll('.category-button').forEach(btn => btn.classList.remove('active'));

        filterAndDisplayProducts();
    }

    // --- THAY ĐỔI LỚN: Hàm này giờ sẽ gọi API backend ---
    async function filterAndDisplayProducts() {
        const searchTerm = searchInput.value.toLowerCase();
        const sortOption = sortSelect.value;
        const categoryId = currentCategoryId; // Lấy ID category hiện tại

        // *** BƯỚC 1: HIỂN THỊ THÔNG BÁO LOADING ***
        productList.innerHTML = '<p class="loading-text">Đang tìm kiếm sản phẩm...</p>';
        paginationControls.innerHTML = '';

        try {
            // *** BƯỚC 2: GỌI API BACKEND ***
            // Xây dựng URL với query params
            const params = new URLSearchParams();
            if (searchTerm) {
                params.append('q', searchTerm);
            }
            if (categoryId) {
                params.append('category_id', categoryId);
            }
            if (sortOption !== 'default') {
                params.append('sort_by', sortOption);
            }

            const response = await fetch(`/api/products/search?${params.toString()}`);
            const results = await response.json();
            
            if (results.error) {
                throw new Error(results.error);
            }
            
            // *** BƯỚC 3 & 4: HIỂN THỊ KẾT QUẢ ***
            // (Backend đã sắp xếp rồi)
            currentProducts = results.products;
            currentPage = 1;
            renderCurrentPage();

        } catch (error) {
            console.error('Lỗi khi tìm kiếm sản phẩm:', error);
            productList.innerHTML = '<p>Đã xảy ra lỗi khi tìm kiếm. Vui lòng thử lại.</p>';
        }
    }
        
    // Hàm để render sản phẩm và các nút chuyển trang (không đổi)
    function renderCurrentPage() {
        displayProducts();
        setupPagination();
    }

    // Hàm để hiển thị danh sách sản phẩm (không đổi)
    function displayProducts() {
        productList.innerHTML = '';
        
        if (currentProducts.length === 0) {
            productList.innerHTML = '<p>Không tìm thấy sản phẩm nào.</p>';
            return;
        }

        const startIndex = (currentPage - 1) * itemsPerPage;
        const endIndex = startIndex + itemsPerPage;
        const pageProducts = currentProducts.slice(startIndex, endIndex);

        pageProducts.forEach(product => {
            const productCard = document.createElement('div');
            productCard.className = 'product-card';
            productCard.innerHTML = `
                <a href="product.html?id=${product.id}" class="product-card-link"> 
                    <img src="${product.image_url}" alt="${product.name}" class="product-image">
                    <div class="product-info">
                        <h3 class="product-name">${product.name}</h3>
                        <p class="product-platform">${product.platform}</p>
                        <p class="product-price">${product.price.toLocaleString('vi-VN')} ₫</p>
                        <span class="buy-button">Xem chi tiết</span> 
                    </div>
                </a>`;
            productList.appendChild(productCard);
        });
    }

    // Hàm để tạo và quản lý các nút chuyển trang (không đổi)
    function setupPagination() {
        paginationControls.innerHTML = '';
        const pageCount = Math.ceil(currentProducts.length / itemsPerPage);

        if (pageCount <= 1) return;

        for (let i = 1; i <= pageCount; i++) {
            const button = document.createElement('button');
            button.innerText = i;
            button.classList.add('page-button');
            if (i === currentPage) {
                button.classList.add('active');
            }
            button.addEventListener('click', () => {
                currentPage = i;
                renderCurrentPage();
                window.scrollTo(0, 0);
            });
            paginationControls.appendChild(button);
        }
    }

    // Gắn sự kiện (không đổi)
    searchButton.addEventListener('click', handleSearchClick);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSearchClick();
        }
    });
    // Thay đổi: Khi sắp xếp cũng phải gọi lại API
    sortSelect.addEventListener('change', () => {
        // Chỉ gọi khi đã có kết quả (đã tìm kiếm hoặc đã chọn category)
        if (currentProducts.length > 0 || searchInput.value || currentCategoryId) {
            filterAndDisplayProducts();
        }
    }); 

    // Bắt đầu chạy ứng dụng (chỉ tải danh mục)
    fetchCategories();
});