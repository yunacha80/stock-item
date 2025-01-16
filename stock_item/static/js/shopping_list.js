document.addEventListener("DOMContentLoaded", function () {
    const incrementBtn = document.getElementById("increment-btn");
    const decrementBtn = document.getElementById("decrement-btn");
    const stockInput = document.getElementById("stock_min_threshold");

        // ボタンで値を増加
    incrementBtn.addEventListener("click", function () {
       let currentValue = parseInt(stockInput.value) || 1;
       stockInput.value = currentValue + 1;
    });

    // ボタンで値を減少
    decrementBtn.addEventListener("click", function () {
       let currentValue = parseInt(stockInput.value) || 1;
        if (currentValue > 1) {
            stockInput.value = currentValue - 1;
        }
    });
});

document.addEventListener("DOMContentLoaded", function () {
    // 在庫の増減ボタン
    document.querySelectorAll(".increment").forEach(button => {
        button.addEventListener("click", function () {
            const input = this.previousElementSibling;
            const itemId = input.dataset.itemId;
            input.value = parseInt(input.value || 0) + 1;
            updateStock(itemId, 1); // 在庫を増やすリクエスト
        });
    });

    document.querySelectorAll(".decrement").forEach(button => {
        button.addEventListener("click", function () {
            const input = this.nextElementSibling;
            const itemId = input.dataset.itemId;
            input.value = Math.max(0, parseInt(input.value || 0) - 1);
            updateStock(itemId, -1); // 在庫を減らすリクエスト
        });
    });

    document.addEventListener("DOMContentLoaded", function () {
        const showAllItemsButton = document.getElementById("show-all-items");
    
        showAllItemsButton.addEventListener("click", function () {
            // すべてのアイテムを表示
            const categories = document.querySelectorAll(".category");
            categories.forEach(category => {
                category.style.display = "block"; // カテゴリを表示
            });
        });
    });


    // 買い物リストに追加
    document.querySelectorAll(".add-to-list").forEach(button => {
        button.addEventListener("click", function () {
            const itemId = this.dataset.itemId;
            addToShoppingList(itemId); // 買い物リストに追加
        });
    });

    // アイテム削除ボタン
    document.querySelectorAll(".delete-item").forEach(button => {
        button.addEventListener("click", function () {
            const itemId = this.dataset.itemId;
            if (confirm("このアイテムを削除してもよろしいですか？")) {
                deleteItem(itemId); // アイテムを削除
            }
        });
    });
});






// 在庫更新
function updateStock(itemId, delta) {
    fetch(`/update-stock/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({ item_id: itemId, delta: delta }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.querySelector(`#item-${itemId} .stock-quantity`).textContent = data.new_quantity;
        }
    });
}

// 買い物リストに追加
function addToShoppingList(itemId) {
    fetch(`/add-to-shopping-list/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({ item_id: itemId }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const button = document.querySelector(`#item-${itemId} .add-to-list`);
            button.textContent = "追加済";
            button.disabled = true;
        }
    });
}

// アイテム削除
function deleteItem(itemId) {
    fetch(`/delete-item/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({ item_id: itemId }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.querySelector(`#item-${itemId}`).remove();
        }
    });
}

function getCSRFToken() {
    return document.querySelector('[name="csrfmiddlewaretoken"]').value;
}
