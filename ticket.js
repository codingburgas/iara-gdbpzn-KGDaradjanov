const API = "http://127.0.0.1:5000";

async function calculate() {
    const data = {
        age: document.getElementById("age").value,
        duration: document.getElementById("duration").value,
        disabled: document.getElementById("disabled").checked
    };

    const res = await fetch(API + "/calculate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    });

    const result = await res.json();

    document.getElementById("price").innerText =
        "Price: " + result.price + " lv.";
}

async function buy() {
    const priceText = document.getElementById("price").innerText;

    if (!priceText) {
        alert("Calculate price first!");
        return;
    }

    const price = priceText
        .replace("Price: ", "")
        .replace(" lv.", "");

    const res = await fetch(API + "/buy", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ price: price })
    });

    const result = await res.json();

    document.getElementById("ticketResult").innerHTML = `
        <h3>🎟️ Ticket</h3>
        <p>ID: ${result.ticket_id}</p>
        <p>Price: ${result.price} lv.</p>
    `;
}