// Lumen: the one shared file that talks to the backend.
const Lumen = (() => {
  const TOKEN_KEY = "lumen_token";

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  }

  function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
  }

  async function request(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    const token = getToken();
    if (token) {
      headers["Authorization"] = "Bearer " + token;
    }

    let response;
    try {
      response = await fetch(path, { ...options, headers });
    } catch (error) {
      throw new Error("Cannot reach the server. Please check your connection.");
    }

    if (response.status === 401 && token) {
      // The login has ended (tokens last one hour): go back to the start.
      clearToken();
      window.location.href = "/app/";
      throw new Error("Your session ended. Please log in again.");
    }

    let data = null;
    if (response.status !== 204) {
      try {
        data = await response.json();
      } catch (error) {
        data = null;
      }
    }

    if (!response.ok) {
      const detail =
        data && typeof data.detail === "string"
          ? data.detail
          : "Something went wrong (error " + response.status + ").";
      throw new Error(detail);
    }

    return data;
  }

  function sendJson(method, path, json) {
    return request(path, {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(json),
    });
  }

  async function login(email, password) {
    clearToken();
    const body = new URLSearchParams({ username: email, password: password });
    const data = await request("/auth/login", { method: "POST", body: body });
    setToken(data.access_token);
  }

  async function startDemo() {
    clearToken();
    const data = await request("/demo/start", { method: "POST" });
    setToken(data.access_token);
  }

  function logOut() {
    clearToken();
    window.location.href = "/app/";
  }

  return {
    getToken: getToken,
    login: login,
    startDemo: startDemo,
    logOut: logOut,
    get: (path) => request(path),
    post: (path, json) => sendJson("POST", path, json),
    patch: (path, json) => sendJson("PATCH", path, json),
    del: (path) => request(path, { method: "DELETE" }),
  };
})();

// End of file