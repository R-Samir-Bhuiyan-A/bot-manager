// app/static/settings.js
const $ = s => document.querySelector(s);
let settings = {};

async function fetchJSON(url, opts={}) {
  const r = await fetch(url, Object.assign({headers:{'Content-Type':'application/json'}}, opts));
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function loadSettings() {
  try {
    settings = await fetchJSON("/api/manager/settings");
    populateForm();
  } catch (error) {
    console.error("Error loading settings", error);
    // Initialize with default settings
    settings = {
      ui: { theme: "dark", refresh_interval: 2000 },
      logs: { max_lines: 1000, auto_scroll: true, buffer_size: 8192 },
      web: { host: "0.0.0.0", port: 8080 }
    };
    populateForm();
  }
}

function populateForm() {
  // Populate UI settings
  if (settings.ui) {
    const themeSelect = $("#ui.theme");
    if (themeSelect) {
      themeSelect.value = settings.ui.theme || "dark";
    }
    
    const refreshInput = $("#ui.refresh_interval");
    if (refreshInput) {
      refreshInput.value = settings.ui.refresh_interval || 2000;
    }
  }
  
  // Populate log settings
  if (settings.logs) {
    const maxLinesInput = $("#logs.max_lines");
    if (maxLinesInput) {
      maxLinesInput.value = settings.logs.max_lines || 1000;
    }
    
    const autoScrollSelect = $("#logs.auto_scroll");
    if (autoScrollSelect) {
      autoScrollSelect.value = settings.logs.auto_scroll ? "true" : "false";
    }
    
    const bufferSizeInput = $("#logs.buffer_size");
    if (bufferSizeInput) {
      bufferSizeInput.value = settings.logs.buffer_size || 8192;
    }
  }
  
  // Populate web settings
  if (settings.web) {
    const hostInput = $("#web.host");
    if (hostInput) {
      hostInput.value = settings.web.host || "0.0.0.0";
    }
    
    const portInput = $("#web.port");
    if (portInput) {
      portInput.value = settings.web.port || 8080;
    }
  }
}

function readForm() {
  const newSettings = {
    ui: {},
    logs: {},
    web: {}
  };
  
  // Read UI settings
  const themeSelect = $("#ui.theme");
  if (themeSelect) {
    newSettings.ui.theme = themeSelect.value;
  }
  
  const refreshInput = $("#ui.refresh_interval");
  if (refreshInput) {
    newSettings.ui.refresh_interval = parseInt(refreshInput.value) || 2000;
  }
  
  // Read log settings
  const maxLinesInput = $("#logs.max_lines");
  if (maxLinesInput) {
    newSettings.logs.max_lines = parseInt(maxLinesInput.value) || 1000;
  }
  
  const autoScrollSelect = $("#logs.auto_scroll");
  if (autoScrollSelect) {
    newSettings.logs.auto_scroll = autoScrollSelect.value === "true";
  }
  
  const bufferSizeInput = $("#logs.buffer_size");
  if (bufferSizeInput) {
    newSettings.logs.buffer_size = parseInt(bufferSizeInput.value) || 8192;
  }
  
  // Read web settings
  const hostInput = $("#web.host");
  if (hostInput) {
    newSettings.web.host = hostInput.value;
  }
  
  const portInput = $("#web.port");
  if (portInput) {
    newSettings.web.port = parseInt(portInput.value) || 8080;
  }
  
  return newSettings;
}

document.addEventListener("DOMContentLoaded", function() {
  // Load settings when the page is loaded
  loadSettings();
  
  // Set up save button
  const saveButton = $("#saveSettings");
  if (saveButton) {
    saveButton.onclick = async () => {
      try {
        const newSettings = readForm();
        const response = await fetch("/api/manager/settings", {
          method: "PUT",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(newSettings)
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        alert("Settings saved successfully!");
      } catch (error) {
        console.error("Error saving settings", error);
        alert("Error saving settings: " + error.message);
      }
    };
  }
});