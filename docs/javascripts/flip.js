// 比較図の切り替え: 1 つのボタンを押すたびに、同じ枠の中で次の図へ入れ替える。
// ボタンの位置も大きさも変わらないので、マウスを動かさずに何度でも見比べられる。
// JavaScript が動かない環境では、CSS だけで横スクロールの並びとして表示される。
document.addEventListener("DOMContentLoaded", () => {
  for (const flip of document.querySelectorAll(".flip")) {
    const items = [...flip.querySelectorAll(":scope > .flip-item")];
    if (items.length < 2) continue;

    const bar = document.createElement("div");
    bar.className = "flip-bar";
    const label = document.createElement("span");
    label.className = "flip-label";
    label.setAttribute("aria-live", "polite");
    const dots = document.createElement("span");
    dots.className = "flip-dots";
    dots.setAttribute("aria-hidden", "true");
    dots.append(...items.map(() => document.createElement("span")));
    const button = document.createElement("button");
    button.type = "button";
    button.className = "flip-button";
    button.innerHTML = '<span class="flip-icon" aria-hidden="true">⟳</span>切り替え';
    bar.append(label, dots, button);

    const stage = document.createElement("div");
    stage.className = "flip-stage";
    stage.append(...items);
    flip.append(bar, stage);
    flip.classList.add("is-enhanced");

    let current = 0;
    const show = i => {
      current = i;
      items.forEach((item, j) => {
        item.classList.toggle("is-current", j === i);
        item.inert = j !== i;
      });
      [...dots.children].forEach((d, j) => d.classList.toggle("on", j === i));
      label.textContent = items[i].dataset.label;
      button.setAttribute("aria-label", `${items[(i + 1) % items.length].dataset.label} に切り替え`);
    };
    button.addEventListener("click", () => {
      show((current + 1) % items.length);
      button.classList.remove("spin");
      void button.offsetWidth; // アニメーションを毎回やり直す
      button.classList.add("spin");
    });
    show(0);
  }
});
