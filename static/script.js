document.addEventListener("DOMContentLoaded", () => {
  const inventoryTable = document.getElementById("inventory-table-body");
  const emptyState = document.getElementById("empty-state");
  const alertsTable = document.getElementById("alerts-table-body");
  const noAlerts = document.getElementById("no-alerts");

  if (inventoryTable) {
    loadInventory();
  }

  if (alertsTable) {
    loadAlerts();
  }

  async function loadInventory() {
    try {
      const res = await fetch("/api/inventory");
      const items = await res.json();

      inventoryTable.innerHTML = "";

      if (items.length === 0) {
        emptyState.classList.remove("hidden");
        return;
      }

      emptyState.classList.add("hidden");

      items.forEach((item) => {
        const row = document.createElement("tr");
        row.id = `row-${item.id}`;
        row.dataset.id = item.id;

        const qtyDisplay = item.quantity < 50
          ? `${item.quantity} <span class="badge-low">Low</span>`
          : item.quantity;

        row.innerHTML = `
          <td><strong>${item.name}</strong></td>
          <td>${item.category}</td>
          <td>${qtyDisplay}</td>
          <td>${item.unit}</td>
          <td>
            <button class="btn-delete" data-id="${item.id}" onclick="deleteItem(${item.id})">Delete</button>
          </td>
        `;

        inventoryTable.appendChild(row);
      });
    } catch (err) {
      console.error("Error loading inventory:", err);
    }
  }

  async function loadAlerts() {
    try {
      const res = await fetch("/api/inventory");
      const items = await res.json();
      const lowStockItems = items.filter((item) => item.quantity < 50);

      alertsTable.innerHTML = "";

      if (lowStockItems.length === 0) {
        noAlerts.classList.remove("hidden");
        return;
      }

      noAlerts.classList.add("hidden");

      lowStockItems.forEach((item) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td><strong>${item.name}</strong></td>
          <td>${item.category}</td>
          <td>${item.quantity} ${item.unit}</td>
          <td><span class="badge-low">Needs Reorder</span></td>
        `;
        alertsTable.appendChild(row);
      });
    } catch (err) {
      console.error("Error loading alerts:", err);
    }
  }

  window.deleteItem = async (id) => {
    const confirmed = confirm("Are you sure you want to remove this item?");
    if (!confirmed) return;

    try {
      const res = await fetch(`/api/inventory/${id}`, { method: "DELETE" });
      if (res.ok) {
        const targetRow = document.getElementById(`row-${id}`);
        if (targetRow) targetRow.remove();

        if (inventoryTable && inventoryTable.children.length === 0) {
          emptyState.classList.remove("hidden");
        }
      }
    } catch (err) {
      console.error("Delete failed:", err);
      alert("Failed to delete item.");
    }
  };
});
