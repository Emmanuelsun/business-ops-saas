// Lumen app: navigation, Dashboard, Enquiries and Reminders screens.
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
    knowledge: "Your saved notes, and the question box that answers from them, will live here.",
  };

  var STATUSES = [
    ["new", "New"],
    ["assigned", "Assigned"],
    ["in_progress", "In progress"],
    ["resolved", "Resolved"],
  ];

  var FILTERS = [
    ["all", "All"],
    ["unsorted", "Needs sorting"],
    ["new", "New"],
    ["assigned", "Assigned"],
    ["in_progress", "In progress"],
    ["resolved", "Resolved"],
  ];

  var view = document.getElementById("view");
  var state = null;
  var ui = { filter: "all", search: "", remindFilter: "pending" };
  var repaint = null;
  var toastTimer = null;
  var toastBox = null;

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

  function toast(text, isError) {
    if (!toastBox) {
      toastBox = el("div", "toast");
      toastBox.setAttribute("role", "status");
      toastBox.setAttribute("aria-live", "polite");
      document.body.appendChild(toastBox);
    }
    toastBox.textContent = text;
    toastBox.className = "toast" + (isError ? " error" : "");
    toastBox.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toastBox.hidden = true;
    }, 2600);
  }

  function customerNames() {
    var names = {};
    state.customers.forEach(function (customer) {
      names[customer.id] = customer.name;
    });
    return names;
  }

  function pendingFollowUps() {
    return state.followUps.filter(function (item) { return item.status === "pending"; });
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

  function field(labelText, control) {
    var label = el("label", "mini-field");
    label.appendChild(el("span", "mini-label", labelText));
    label.appendChild(control);
    return label;
  }

  // Sends one change to the server, then shows what is really saved.
  async function save(enquiry, path, body, select) {
    select.disabled = true;
    try {
      var updated = await Lumen.patch(path, body);
      Object.assign(enquiry, updated);
      toast("Saved");
    } catch (error) {
      toast(error.message, true);
    }
    if (repaint) {
      repaint();
    }
  }

  function actionsFor(enquiry) {
    var box = el("div", "row-actions");

    var statusSelect = el("select", "input select");
    STATUSES.forEach(function (pair) {
      var option = el("option", null, pair[1]);
      option.value = pair[0];
      statusSelect.appendChild(option);
    });
    statusSelect.value = enquiry.status;
    statusSelect.addEventListener("change", function () {
      save(
        enquiry,
        "/enquiries/" + enquiry.id + "/status",
        { status: statusSelect.value },
        statusSelect
      );
    });
    box.appendChild(field("Status", statusSelect));

    if (state.me.role === "owner" && state.users.length) {
      var assignSelect = el("select", "input select");
      if (!enquiry.assigned_to) {
        var none = el("option", null, "Not assigned");
        none.value = "";
        none.disabled = true;
        assignSelect.appendChild(none);
      }
      state.users.forEach(function (user) {
        var option = el("option", null, user.full_name);
        option.value = String(user.id);
        assignSelect.appendChild(option);
      });
      assignSelect.value = enquiry.assigned_to ? String(enquiry.assigned_to) : "";
      assignSelect.addEventListener("change", function () {
        save(
          enquiry,
          "/enquiries/" + enquiry.id + "/assign",
          { assigned_to: Number(assignSelect.value) },
          assignSelect
        );
      });
      box.appendChild(field("Assigned to", assignSelect));
    }

    return box;
  }

  function enquiryRow(enquiry, customerName, detailed) {
    var row = el("article", "card row-card");

    var head = el("div", "row-head");
    head.appendChild(el("span", "row-name", customerName));
    head.appendChild(el("span", "row-time", timeAgo(enquiry.created_at)));
    row.appendChild(head);

    row.appendChild(el("p", detailed ? "row-message full" : "row-message", enquiry.message));

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

    if (detailed) {
      row.appendChild(actionsFor(enquiry));
    }

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
    stats.appendChild(
      statCard("Reminders", pendingFollowUps().length, "Drafts to review", "#reminders")
    );
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

    var names = customerNames();
    var list = el("div", "list");
    var recent = enquiries
      .slice()
      .sort(function (a, b) { return b.id - a.id; })
      .slice(0, 5);

    if (!recent.length) {
      list.appendChild(el("div", "card empty", "No enquiries yet."));
    }
    recent.forEach(function (enquiry) {
      list.appendChild(enquiryRow(enquiry, names[enquiry.customer_id] || "Customer", false));
    });
    view.appendChild(list);
  }

  function matchesFilter(enquiry, key) {
    if (key === "all") {
      return true;
    }
    if (key === "unsorted") {
      return enquiry.needs_manual_sorting;
    }
    return enquiry.status === key;
  }

  function renderEnquiries() {
    view.appendChild(el("h1", "page-title", "Enquiries"));
    view.appendChild(el("p", "page-sub", "Every customer message, sorted and assigned."));

    var search = el("input", "input search");
    search.type = "search";
    search.placeholder = "Search by customer or message";
    search.value = ui.search;
    search.setAttribute("aria-label", "Search enquiries");
    view.appendChild(search);

    var chips = el("div", "chips");
    view.appendChild(chips);
    var summary = el("p", "list-summary");
    view.appendChild(summary);
    var list = el("div", "list");
    view.appendChild(list);

    var names = customerNames();

    function paint() {
      chips.textContent = "";
      FILTERS.forEach(function (pair) {
        var total = state.enquiries.filter(function (e) {
          return matchesFilter(e, pair[0]);
        }).length;

        var chip = el("button", "chip" + (ui.filter === pair[0] ? " active" : ""));
        chip.type = "button";
        chip.setAttribute("aria-pressed", ui.filter === pair[0] ? "true" : "false");
        chip.appendChild(document.createTextNode(pair[1]));
        chip.appendChild(el("span", "chip-count", String(total)));
        chip.addEventListener("click", function () {
          ui.filter = pair[0];
          paint();
        });
        chips.appendChild(chip);
      });

      var term = ui.search.trim().toLowerCase();
      var shown = state.enquiries
        .filter(function (e) {
          if (!matchesFilter(e, ui.filter)) {
            return false;
          }
          if (!term) {
            return true;
          }
          var name = (names[e.customer_id] || "").toLowerCase();
          return name.indexOf(term) !== -1 || e.message.toLowerCase().indexOf(term) !== -1;
        })
        .sort(function (a, b) { return b.id - a.id; });

      summary.textContent = "Showing " + shown.length + " of " + state.enquiries.length;
      list.textContent = "";
      if (!shown.length) {
        list.appendChild(el("div", "card empty", "No enquiries match."));
      }
      shown.forEach(function (enquiry) {
        list.appendChild(enquiryRow(enquiry, names[enquiry.customer_id] || "Customer", true));
      });
    }

    repaint = paint;
    search.addEventListener("input", function () {
      ui.search = search.value;
      paint();
    });
    paint();
  }

  function renderReminders() {
    view.appendChild(el("h1", "page-title", "Reminders"));
    view.appendChild(
      el(
        "p",
        "page-sub",
        "Follow-up drafts to review. Nothing is ever sent to a customer automatically."
      )
    );

    if (state.me.role === "owner") {
      var tool = el("div", "card tool-card");
      tool.appendChild(el("h3", null, "Check for stale enquiries"));
      tool.appendChild(
        el(
          "p",
          null,
          "Finds enquiries with no activity for 2 days and drafts a friendly reminder for each. Uses up to 3 AI calls."
        )
      );
      var runButton = el("button", "btn btn-gold btn-small", "Run the check");
      runButton.type = "button";
      runButton.addEventListener("click", async function () {
        runButton.disabled = true;
        runButton.textContent = "Checking...";
        try {
          var result = await Lumen.post("/follow-ups/run?days=2&limit=3", {});
          state.followUps = await Lumen.get("/follow-ups");
          state.usage = await Lumen.get("/usage");
          ui.remindFilter = "pending";
          if (result.created) {
            toast(
              "Created " + result.created + " reminder(s), " + result.drafted + " drafted by AI"
            );
          } else {
            toast("Nothing needs a reminder right now");
          }
        } catch (error) {
          toast(error.message, true);
        }
        runButton.disabled = false;
        runButton.textContent = "Run the check";
        paint();
      });
      tool.appendChild(runButton);
      view.appendChild(tool);
    }

    var chips = el("div", "chips");
    view.appendChild(chips);
    var list = el("div", "list");
    view.appendChild(list);

    var names = customerNames();
    var byId = {};
    state.enquiries.forEach(function (enquiry) {
      byId[enquiry.id] = enquiry;
    });

    function reminderCard(item) {
      var enquiry = byId[item.enquiry_id];
      var card = el("article", "card row-card");

      var head = el("div", "row-head");
      head.appendChild(
        el("span", "row-name", enquiry ? names[enquiry.customer_id] || "Customer" : "Customer")
      );
      head.appendChild(el("span", "row-time", timeAgo(item.created_at)));
      card.appendChild(head);

      if (enquiry) {
        card.appendChild(el("p", "row-message full", enquiry.message));
      }

      card.appendChild(el("div", "draft-label", "Suggested follow-up. Please check it before sending."));
      if (item.draft_message) {
        card.appendChild(el("div", "draft", item.draft_message));
      } else {
        card.appendChild(
          el("p", "notice notice-gold", "No draft was written for this one. Please write it yourself.")
        );
      }

      var buttons = el("div", "row-buttons");

      if (item.draft_message) {
        var copy = el("button", "btn btn-ghost btn-small", "Copy draft");
        copy.type = "button";
        copy.addEventListener("click", function () {
          if (!navigator.clipboard) {
            toast("Copying is not available here", true);
            return;
          }
          navigator.clipboard.writeText(item.draft_message).then(
            function () { toast("Draft copied"); },
            function () { toast("Could not copy the draft", true); }
          );
        });
        buttons.appendChild(copy);
      }

      if (item.status === "pending") {
        var done = el("button", "btn btn-primary btn-small", "Mark as done");
        done.type = "button";
        done.addEventListener("click", async function () {
          done.disabled = true;
          try {
            var updated = await Lumen.patch("/follow-ups/" + item.id + "/done", {});
            Object.assign(item, updated);
            toast("Marked as done");
          } catch (error) {
            toast(error.message, true);
          }
          paint();
        });
        buttons.appendChild(done);
      } else {
        buttons.appendChild(badge("done", "badge-done"));
      }

      card.appendChild(buttons);
      return card;
    }

    function paint() {
      var pending = pendingFollowUps();
      var finished = state.followUps.filter(function (item) { return item.status === "done"; });

      chips.textContent = "";
      [
        ["pending", "Waiting", pending.length],
        ["done", "Done", finished.length],
      ].forEach(function (entry) {
        var chip = el("button", "chip" + (ui.remindFilter === entry[0] ? " active" : ""));
        chip.type = "button";
        chip.setAttribute("aria-pressed", ui.remindFilter === entry[0] ? "true" : "false");
        chip.appendChild(document.createTextNode(entry[1]));
        chip.appendChild(el("span", "chip-count", String(entry[2])));
        chip.addEventListener("click", function () {
          ui.remindFilter = entry[0];
          paint();
        });
        chips.appendChild(chip);
      });

      var shown = (ui.remindFilter === "done" ? finished : pending)
        .slice()
        .sort(function (a, b) { return b.id - a.id; });

      list.textContent = "";
      if (!shown.length) {
        list.appendChild(
          el(
            "div",
            "card empty",
            ui.remindFilter === "done"
              ? "Nothing has been marked as done yet."
              : "No reminders waiting. You are all caught up."
          )
        );
      }
      shown.forEach(function (item) {
        list.appendChild(reminderCard(item));
      });
    }

    repaint = paint;
    paint();
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
    repaint = null;
    view.textContent = "";
    if (id === "dashboard") {
      renderDashboard();
    } else if (id === "enquiries") {
      renderEnquiries();
    } else if (id === "reminders") {
      renderReminders();
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
      var me = await Lumen.get("/auth/me");
      var requests = [
        Lumen.get("/usage"),
        Lumen.get("/enquiries"),
        Lumen.get("/customers"),
        Lumen.get("/follow-ups"),
      ];
      if (me.role === "owner") {
        requests.push(Lumen.get("/users"));
      }
      var results = await Promise.all(requests);

      state = {
        me: me,
        usage: results[0],
        enquiries: results[1],
        customers: results[2],
        followUps: results[3],
        users: results[4] || [],
      };
      document.getElementById("user-name").textContent = me.full_name;
      document.getElementById("user-role").textContent = capitalize(me.role);
      render();
    } catch (error) {
      view.textContent = "";
      view.appendChild(el("p", "notice", error.message));
    }
  }

  start();
})();

// End of file