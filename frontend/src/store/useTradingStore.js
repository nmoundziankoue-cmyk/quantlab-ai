import { create } from "zustand";

const useTradingStore = create((set, get) => ({
  // Active paper account
  activePaperAccountId: null,
  setActivePaperAccountId: (id) => set({ activePaperAccountId: id }),

  // Active order filter state
  orderFilters: {
    status: "",
    ticker: "",
    page: 1,
    page_size: 50,
  },
  setOrderFilter: (key, value) =>
    set((s) => ({ orderFilters: { ...s.orderFilters, [key]: value, page: 1 } })),
  setOrderPage: (page) =>
    set((s) => ({ orderFilters: { ...s.orderFilters, page } })),

  // Order ticket state (for the new-order form)
  orderTicket: {
    ticker: "",
    side: "BUY",
    orderType: "MARKET",
    quantity: "",
    limitPrice: "",
    stopPrice: "",
    timeInForce: "DAY",
    strategyTag: "",
    notes: "",
  },
  setOrderTicketField: (key, value) =>
    set((s) => ({ orderTicket: { ...s.orderTicket, [key]: value } })),
  resetOrderTicket: () =>
    set({
      orderTicket: {
        ticker: "",
        side: "BUY",
        orderType: "MARKET",
        quantity: "",
        limitPrice: "",
        stopPrice: "",
        timeInForce: "DAY",
        strategyTag: "",
        notes: "",
      },
    }),

  // Order preview result
  orderPreview: null,
  setOrderPreview: (preview) => set({ orderPreview: preview }),
  clearOrderPreview: () => set({ orderPreview: null }),

  // Blotter filter state
  blotterFilters: {
    ticker: "",
    side: "",
    strategy_tag: "",
    since: "",
    until: "",
    page: 1,
    page_size: 100,
  },
  setBlotterFilter: (key, value) =>
    set((s) => ({ blotterFilters: { ...s.blotterFilters, [key]: value, page: 1 } })),

  // Execution analytics date range
  analyticsDateRange: { since: "", until: "" },
  setAnalyticsDateRange: (range) => set({ analyticsDateRange: range }),

  // Active tab in Trading page
  tradingTab: "order-ticket",
  setTradingTab: (tab) => set({ tradingTab: tab }),

  // Notification queue for in-app alerts
  notifications: [],
  addNotification: (notification) =>
    set((s) => ({
      notifications: [
        { id: Date.now(), ...notification },
        ...s.notifications.slice(0, 49),
      ],
    })),
  dismissNotification: (id) =>
    set((s) => ({
      notifications: s.notifications.filter((n) => n.id !== id),
    })),
  clearNotifications: () => set({ notifications: [] }),
}));

export default useTradingStore;
