document.addEventListener("DOMContentLoaded", function () {
    // 増減ボタンの処理
    document.querySelectorAll(".increment").forEach(button => {
        button.addEventListener("click", function () {
            const input = this.previousElementSibling; // +ボタンの前の要素を取得
            if (input && input.tagName === "INPUT" && input.type === "number") {
                input.value = parseInt(input.value || 0) + 1; // 数値を増加
            }
        });
    });

    document.querySelectorAll(".decrement").forEach(button => {
        button.addEventListener("click", function () {
            const input = this.nextElementSibling; // -ボタンの次の要素を取得
            if (input && input.tagName === "INPUT" && input.type === "number") {
                input.value = Math.max(0, parseInt(input.value || 0) - 1); // 数値を減少（0以下にはしない）
            }
        });
    });


    document.addEventListener("DOMContentLoaded", function () {
        const toggles = document.querySelectorAll(".toggle-suggestion");
    
        toggles.forEach((toggle) => {
            toggle.addEventListener("click", () => {
                const details = toggle.nextElementSibling;
                details.classList.toggle("hidden");
            });
        });
    });    
});
