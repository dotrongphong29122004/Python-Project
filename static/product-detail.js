document.addEventListener('DOMContentLoaded', () => {
    const productDetailContainer = document.getElementById('product-detail-container');
    const params = new URLSearchParams(window.location.search);
    const productId = params.get('id');

    if (!productId) {
        productDetailContainer.innerHTML = '<h1>Không tìm thấy ID sản phẩm.</h1>';
        return;
    }

    // --- THAY ĐỔI: Gọi API chi tiết sản phẩm ---
    async function fetchProductData() {
        try {
            // Gọi API backend cho 1 sản phẩm
            const response = await fetch(`/api/product/${productId}`); 
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json(); // Data giờ là { product: {...}, related_products: [...] }

            if (data.product) {
                displayProductDetails(data.product);
                displayRelatedProducts(data.related_products);
            } else {
                productDetailContainer.innerHTML = '<h1>Sản phẩm không tồn tại.</h1>';
            }
        } catch (error) {
            console.error('Lỗi khi tải dữ liệu:', error);
            productDetailContainer.innerHTML = '<h1>Đã xảy ra lỗi khi tải thông tin.</h1>';
        }
    }


// THAY THẾ TOÀN BỘ HÀM CŨ BẰNG HÀM MỚI NÀY

function displayProductDetails(product) {
    // Cập nhật tiêu đề trang
    document.title = product.name;

    // Tạo các đường link tìm kiếm sản phẩm trên từng sàn
    const searchName = encodeURIComponent(product.name);
    const tikiSearchUrl = `https://tiki.vn/search?q=${searchName}`;
    const shopeeSearchUrl = `https://shopee.vn/search?keyword=${searchName}`;
    const lazadaSearchUrl = `https://www.lazada.vn/catalog/?q=${searchName}`;
    const chototSearchUrl = `https://www.chotot.com/mua-ban?q=${searchName}`;
    const dmxSearchUrl = `https://www.dienmayxanh.com/search?key=${searchName}`;

    // Luôn tạo link ĐMX
    const dmxLinkHtml = `
        <a href="${dmxSearchUrl}" target="_blank" class="platform-link">
            <img src="https://thuvienvector.vn/wp-content/uploads/2025/08/dien-may-xanh-logo-png.jpg" >
        </a>
    `;

    productDetailContainer.innerHTML = `
        <div class="product-detail-image">
            <img src="${product.image_url}" alt="${product.name}">
        </div>
        <div class="product-detail-info">
            <h1 class="product-title">${product.name}</h1>

            <div class="product-price-detail">${product.price.toLocaleString('vi-VN')} ₫</div>

            <a href="${product.url}" target="_blank" class="buy-now-button">Đến nơi bán (${product.platform})</a>
            <div class="seller-platforms">
                <h3>Tìm và so sánh giá trên các sàn khác:</h3>
                <div class="platform-links">
                    <a href="${tikiSearchUrl}" target="_blank" class="platform-link">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/4/43/Logo_Tiki_2023.png" alt="Tìm trên Tiki">
                    </a>
                    <a href="${shopeeSearchUrl}" target="_blank" class="platform-link">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/0/0e/Shopee_logo.svg" alt="Tìm trên Shopee"> 
                    </a>
                    <a href="${lazadaSearchUrl}" target="_blank" class="platform-link">
                        <img src="https://brasol.vn/wp-content/uploads/2022/09/logo-lazada-png.png" alt="Tìm trên Lazada">
                    </a>
                    <a href="${chototSearchUrl}" target="_blank" class="platform-link">
                        <img src="https://c.smartrecruiters.com/sr-company-images-prod-aws-dc5/62e4896252733a296750c7cd/a293449f-b8a5-4faf-acec-e88ab7550390/huge?r=s3-eu-central-1&_1663551719302" alt="Tìm trên Chợ Tốt">
                    </a>
                    ${dmxLinkHtml}
                </div>
            </div>

            <div class="product-description">
                <h2>Mô tả sản phẩm</h2>
                <p>${product.description || 'Chưa có mô tả chi tiết cho sản phẩm này.'}</p>
            </div>
        </div>
    `;
}

    // Hàm displayRelatedProducts (Không đổi)
    function displayRelatedProducts(products) {
        const relatedListContainer = document.getElementById('related-products-list');
        const relatedSection = document.querySelector('.related-products-section');

        if (products.length === 0) {
            relatedSection.style.display = 'none';
            return;
        }

        relatedListContainer.innerHTML = '';
        products.forEach(product => {
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
            relatedListContainer.appendChild(productCard);
        });
    }

    fetchProductData();
});