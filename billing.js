// Billing and checkout functions

function createOrder() {
    return fetch('/create_order', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            return data;
        } else {
            throw new Error(data.error || 'Failed to create order');
        }
    });
}

function generateQRCode(amount) {
    return `/generate_qr/${amount}`;
}

function printBill(orderId) {
    window.open(`/bill/${orderId}`, '_blank');
}

// Checkout page initialization
document.addEventListener('DOMContentLoaded', function() {
    const checkoutPage = document.querySelector('.checkout-container');
    if (checkoutPage) {
        loadCheckoutSummary();
    }
});

function loadCheckoutSummary() {
    fetch('/cart')
        .then(response => response.json())
        .then(data => {
            if (data.items.length === 0) {
                window.location.href = '/';
                return;
            }
            updateCheckoutDisplay(data);
        })
        .catch(error => {
            console.error('Error loading checkout:', error);
        });
}

function updateCheckoutDisplay(cartData) {
    // This will be handled by the checkout.html inline script
    // This file provides utility functions
}
