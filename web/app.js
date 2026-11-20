// Lumen app: navigation and the Dashboard screen.
(function () {
  if (!Lumen.getToken()) {
    window.location.href = "/app/";
    return;
  }

  var ICON_ATTRS =
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"';

  // The icons below are fixed drawings written by us, never server data.
  var NAV = [
    {
      id: "dashboard",
      label: "Dashboard",
      icon:
        '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/>' +
        '<rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    },
    {
      id: "enquiries",
      label: "Enquiries",
      icon: '<path d="M3 13l2.5-8h13L21 13"/><path d="M3 13v6h18v-6h-5l-1.5 2.5h-5L8 13z"/>',
    },
    {
      id: "reminders",
      label: "Reminders",
      icon: '<path d="M6 9a6 6 0 0 1 12 0c0 6 2 7 2 7H4s2-1 2-7"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    },
    {
      id: "knowledge",
      label: "Knowledge",
      icon: '<path d="M5 4h10a4 4 0 0 1 4 4v12H9a4 4 0 0 1-4-4z"/><path d="M5 16a4 4 0 0 1 4-4h10"/>',
    },
  ];

  var COMING = {
    enquiries: "Every enquiry, with its category, priority and owner, will live here.",
    reminders: "Follow-up drafts waiting for your review will live here.",
    knowledge: "Your saved notes, and the question box that answers from them, will live here.",
  };

  var view = document.getElementById("view");
  var state = null;

  // Builds an element. The text is always placed as plain text, never as HTML.
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text !== undefined && text !== null) {
      node.textContent = text;
    }
    return node;
  }

  function capitalize(text) {
    return text ? text.charAt(0).toUpperCase() + text.slice(1) : "";
  }

  function timeAgo(iso) {
    if (!iso) {
      return "";
    }
    var days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
    if (days <= 0) {
      return "today";
    }
    if (days === 1) {
      return "yesterday";
    }
    return days + " days ago";
  }

  function buildNav(container) {
    NAV.forEach(function (item) {
      var link = el("a", "nav-link");
      link.href = "#" + item.id;
      link.setAttribute("data-id", item.id);

      var icon = el("span", "nav-icon");
      icon.innerHTML = "<svg " + ICON_ATTRS + ">" + item.icon + "</svg>";
      link.appendChild(icon);
      link.appendChild(el("span", "nav-label", item.label));
      container.appendChild(link);
    });
  }

  function currentId() {
    var id = window.location.hash.replace("#", "");
    return NAV.some(function (item) { return item.id === id; }) ? id : "dashboard";
  }

  function highlight(id) {
    document.querySelectorAll(".nav-link").forEach(function (link) {
      var active = link.getAttribute("data-id") === id;
      link.classList.toggle("active", active);
      if (active) {
        link.setAttribute("aria-current", "page");
      } else {
        link.removeAttribute("aria-current");
      }
    });
  }

  function badge(text, className) {
    return el("span", "badge " + className, text);
  }

  function statCard(label, value, note, href, percent) {
    var card = el(href ? "a" : "div", "card stat-card");
    if (href) {
      card.href = href;
    }
    card.appendChild(el("div", "stat-label", label));
    card.appendChild(el("div", "stat-value", String(value)));

    if (percent !== undefined) {
      var meter = el("div", "meter");
      var fill = el("div", "meter-fill");
      fill.style.width = percent + "%";
      meter.appendChild(fill);
      card.appendChild(meter);
    }

    card.appendChild(el("p", "stat-note", note));
    return card;
  }

  function enquiryRow(enquiry, customerName) {
    var row = el("article", "card row-card");

    var head = el("div", "row-head");
    head.appendChild(el("span", "row-name", customerName));
    head.appendChild(el("span", "row-time", timeAgo(enquiry.created_at)));
    row.appendChild(head);

    row.appendChild(el("p", "row-message", enquiry.message));

    var badges = el("div", "badges");
    if (enquiry.needs_manual_sorting) {
      badges.appendChild(badge("needs sorting", "badge-warn"));
    } else {
      if (enquiry.category) {
        badges.appendChild(badge(enquiry.category, "badge-category"));
      }
      if (enquiry.priority) {
        var priorityClass =
          { high: "badge-high", medium: "badge-medium" }[enquiry.priority] || "badge-neutral";
        badges.appendChild(badge(enquiry.priority + " priority", priorityClass));
      }
    }
    var statusClass = enquiry.status === "resolved" ? "badge-done" : "badge-neutral";
    badges.appendChild(badge(enquiry.status.replace("_", " "), statusClass));
    row.appendChild(badges);

    return row;
  }

  function renderDashboard() {
    var usage = state.usage;
    var enquiries = state.enquiries;

    var open = enquiries.filter(function (e) { return e.status !== "resolved"; }).length;
    var unsorted = enquiries.filter(function (e) { return e.needs_manual_sorting; }).length;
    var firstName = state.me.full_name.split(" ")[0];

    view.appendChild(el("h1", "page-title", "Hello, " + firstName));
    view.appendChild(el("p", "page-sub", "Here is what needs your attention today."));

    if (usage.is_demo) {
      view.appendChild(
        el(
          "p",
          "notice notice-gold demo-note",
          "You are exploring a demo with sample data. It is private to you and is cleared automatically after 24 hours."
        )
      );
    }

    var percent =
      usage.ai_call_limit > 0
        ? Math.min(100, Math.round((usage.ai_calls_used / usage.ai_call_limit) * 100))
        : 0;

    var stats = el("div", "stats");
    stats.appendChild(statCard("Open enquiries", open, "of " + enquiries.length + " in total", "#enquiries"));
    stats.appendChild(
      statCard("Need sorting", unsorted, unsorted ? "Waiting for a person" : "All sorted", "#enquiries")
    );
    stats.appendChild(statCard("Reminders", state.followUps.length, "Drafts to review", "#reminders"));
    stats.appendChild(
      statCard(
        "AI calls used",
        usage.ai_calls_used + " / " + usage.ai_call_limit,
        capitalize(usage.plan) + " plan",
        null,
        percent
      )
    );
    view.appendChild(stats);

    var head = el("div", "section-head");
    head.appendChild(el("h2", null, "Recent enquiries"));
    var seeAll = el("a", "text-link", "See all");
    seeAll.href = "#enquiries";
    head.appendChild(seeAll);
    view.appendChild(head);

    var names = {};
    state.customers.forEach(function (customer) {
      names[customer.id] = customer.name;
    });

    var list = el("div", "list");
    var recent = enquiries
      .slice()
      .sort(function (a, b) { return b.id - a.id; })
      .slice(0, 5);

    if (!recent.length) {
      list.appendChild(el("div", "card empty", "No enquiries yet."));
    }
    recent.forEach(function (enquiry) {
      list.appendChild(enquiryRow(enquiry, names[enquiry.customer_id] || "Customer"));
    });
    view.appendChild(list);
  }

  function renderComing(id) {
    var item = NAV.filter(function (n) { return n.id === id; })[0];
    view.appendChild(el("h1", "page-title", item.label));
    view.appendChild(el("p", "page-sub", "This screen is coming in the next step."));
    var card = el("div", "card");
    card.appendChild(el("p", null, COMING[id]));
    view.appendChild(card);
  }

  function render() {
    var id = currentId();
    highlight(id);
    if (!state) {
      return;
    }
    view.textContent = "";
    if (id === "dashboard") {
      renderDashboard();
    } else {
      renderComing(id);
    }
    window.scrollTo(0, 0);
  }

  async function start() {
    buildNav(document.getElementById("side-nav"));
    buildNav(document.getElementById("bottom-nav"));
    document.querySelectorAll("[data-logout]").forEach(function (button) {
      button.addEventListener("click", Lumen.logOut);
    });
    window.addEventListener("hashchange", render);
    highlight(currentId());

    view.appendChild(el("p", "page-sub", "Loading your workspace..."));

    try {
      var results = await Promise.all([
        Lumen.get("/auth/me"),
        Lumen.get("/usage"),
        Lumen.get("/enquiries"),
        Lumen.get("/customers"),
        Lumen.get("/follow-ups?status=pending"),
      ]);
      state = {
        me: results[0],
        usage: results[1],
        enquiries: results[2],
        customers: results[3],
        followUps: results[4],
      };
      document.getElementById("user-name").textContent = state.me.full_name;
      document.getElementById("user-role").textContent = capitalize(state.me.role);
      render();
    } catch (error) {
      view.textContent = "";
      view.appendChild(el("p", "notice", error.message));
    }
  }

  start();
})();

// End of file