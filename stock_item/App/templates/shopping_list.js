document.addEventListener("DOMContentLoaded", function () {
    // 購入済みのアイテムを更新する処理
    document.querySelector("#update-list").addEventListener("click", function () {
        const purchasedItems = Array.from(document.querySelectorAll(".mark-purchased:checked"));
        
        purchasedItems.forEach(checkbox => {
            const row = checkbox.closest("tr");
            const itemId = checkbox.dataset.id;
            const purchasedQuantity = row.querySelector(".purchased-quantity").value;
            const purchasedDate = row.querySelector(".purchased-date").value;

            if (!purchasedQuantity || purchasedQuantity <= 0) {
                alert("購入数を正しく入力してください。");
                return;
            }

            if (!purchasedDate) {
                alert("購入日を入力してください。");
                return;
            }

            fetch(`/update_stock_and_history/${itemId}/`, {
                method: "POST",
                headers: {
                    "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').getAttribute("content"),
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    purchased_quantity: purchasedQuantity,
                    purchased_date: purchasedDate
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.removed) {
                    row.remove(); // リストから削除
                }
                alert("更新が完了しました！");
            })
            .catch(error => {
                console.error("更新エラー:", error);
                alert("エラーが発生しました。");
            });
        });
    });

    // 買い回り提案の処理
    document.querySelector("#suggest-stores-btn").addEventListener("click", function () {
        const selectedItems = Array.from(document.querySelectorAll(".select-item:checked"))
                                   .map(checkbox => checkbox.dataset.id);

        if (selectedItems.length === 0) {
            alert("提案するアイテムを選択してください。");
            return;
        }

        fetch(`/suggest_stores/?item_ids=${selectedItems.join(",")}`)
            .then(response => response.json())
            .then(data => {
                const suggestionsList = document.querySelector("#suggestions-list");
                suggestionsList.innerHTML = ""; // 既存の提案をクリア

                data.suggestions.forEach(suggestion => {
                    const listItem = document.createElement("li");
                    listItem.textContent = `${suggestion.item} の提案:`;

                    const storeList = document.createElement("ul");
                    suggestion.stores.forEach(store => {
                        const storeItem = document.createElement("li");
                        storeItem.textContent = `${store.name}: ¥${store.price}`;
                        storeList.appendChild(storeItem);
                    });

                    listItem.appendChild(storeList);
                    suggestionsList.appendChild(listItem);
                });
            })
            .catch(error => {
                console.error("提案エラー:", error);
                alert("提案の取得に失敗しました。");
            });
    });
});
