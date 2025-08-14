// app/static/botpage.js
const $ = s => document.querySelector(s);
const params = new URLSearchParams(location.search);
const botId = params.get("id");
let statusWS = null, logWS = null, schema = null, config = null;

function badge(s){
  if (s==="running") return '<span class="bot-status running"><i class="fas fa-circle"></i> running</span>';
  if (s==="stopped") return '<span class="bot-status stopped"><i class="fas fa-circle"></i> stopped</span>';
  return `<span class="bot-status error"><i class="fas fa-exclamation-circle"></i> ${s}</span>`;
}

async function fetchJSON(url, opts={}){
  const r = await fetch(url, Object.assign({headers:{'Content-Type':'application/json'}}, opts));
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function openStatusWS(){
  if (statusWS) statusWS.close();
  statusWS = new WebSocket(`${location.origin.replace("http","ws")}/ws/status`);
  statusWS.onmessage = ev => {
    try {
      const list = JSON.parse(ev.data);
      const b = list.find(x=>x.id===botId);
      if (!b) return;
      
      // Update bot title and status
      $("#bot-title").textContent = b.name;
      $("#bot-status").outerHTML = badge(b.status);
      $("#bot-id").textContent = b.id;
      $("#process-id").textContent = b.pid || "-";
      $("#cpu-usage").textContent = `${b.cpu}%`;
      $("#memory-usage").textContent = `${b.memory_mb} MB`;
      
      // Update download logs link
      $("#dlLogs").href = `/api/bots/${b.id}/logs`;
      
      // Update button states
      if (b.status === "running") {
        $("#startBtn").disabled = true;
        $("#stopBtn").disabled = false;
        $("#restartBtn").disabled = false;
      } else {
        $("#startBtn").disabled = false;
        $("#stopBtn").disabled = true;
        $("#restartBtn").disabled = true;
      }
    } catch (error) {
      console.error("Error processing status update", error);
    }
  };
  statusWS.onclose = () => setTimeout(openStatusWS, 1500);
  statusWS.onerror = (error) => console.error("Status WebSocket error", error);
}

async function post(url){ 
  try {
    const response = await fetch(url, {method:"POST"});
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response;
  } catch (error) {
    console.error("Error posting to", url, error);
    alert("Error: " + error.message);
  }
}

$("#startBtn").onclick = () => post(`/api/bots/${botId}/start`);
$("#stopBtn").onclick = () => post(`/api/bots/${botId}/stop`);
$("#restartBtn").onclick = () => post(`/api/bots/${botId}/restart`);

function openLogWS(){
  if (logWS) logWS.close();
  
  const logBox = $("#logbox");
  logBox.textContent = "Connecting to log stream...\n";
  
  $("#logStatus").innerHTML = `
    <i class="fas fa-circle-notch fa-spin"></i>
    <span>Connecting to log stream...</span>
  `;
  
  try {
    logWS = new WebSocket(`${location.origin.replace("http","ws")}/ws/logs/${botId}`);
    
    logWS.onopen = () => {
      $("#logStatus").innerHTML = `
        <i class="fas fa-circle text-success"></i>
        <span>Connected and listening for logs...</span>
      `;
      logBox.textContent = ""; // Clear connection message
    };
    
    logWS.onmessage = ev => {
      const box = $("#logbox");
      const message = ev.data + "\n";
      
      // Add new log line
      box.textContent += message;
      
      // Auto-scroll to bottom if user is near the bottom
      const isScrolledToBottom = box.scrollHeight - box.clientHeight <= box.scrollTop + 10;
      if (isScrolledToBottom) {
        box.scrollTop = box.scrollHeight;
      }
    };
    
    logWS.onerror = (error) => {
      console.error("Log WebSocket error", error);
      $("#logStatus").innerHTML = `
        <i class="fas fa-exclamation-circle text-danger"></i>
        <span>Error: ${error.message || "Connection error"}</span>
      `;
    };
    
    logWS.onclose = () => setTimeout(openLogWS, 2000);
  } catch (error) {
    console.error("Error opening log WebSocket", error);
    $("#logStatus").innerHTML = `
      <i class="fas fa-exclamation-circle text-danger"></i>
      <span>Error: ${error.message || "Failed to connect"}</span>
    `;
  }
}

// Configuration field descriptions
const CONFIG_DESCRIPTIONS = {
  discord_user_token: "Your Discord user token for authentication",
  gemini_api_key: "Google Gemini API key for AI responses",
  channel_ids: "List of channel IDs the bot will monitor (one per line)",
  "persona.name": "Name of your bot persona",
  "persona.style": "Bot's communication style (e.g., casual, formal)",
  "persona.quirks": "Bot's personality quirks and traits",
  "persona.boundaries": "Bot's behavioral boundaries and restrictions",
  "persona.mood_daily_drift": "Amount mood can drift per day (0..1)",
  "persona.moods": "List of possible moods for the bot (one per line)",
  "persona.mood_change_probability": "Chance to change mood after a reply",
  "reply.max_reply_chars": "Maximum characters in a reply",
  "reply.min_delay_sec": "Minimum delay before replying (seconds)",
  "reply.max_delay_sec": "Maximum delay before replying (seconds)",
  "reply.typing_speed_wpm": "Typing speed in words per minute",
  "reply.multi_msg_probability": "Chance to split into 2-3 short messages",
  "reply.outside_hours_reply_prob": "Reply probability outside active hours",
  "reply.public_probs.stranger": "Reply chance for strangers (score 0-10)",
  "reply.public_probs.acquaintance": "Reply chance for acquaintances (score 11-50)",
  "reply.public_probs.friend": "Reply chance for friends (score 51-100)",
  "reply.public_probs.bestfriend": "Reply chance for best friends (score 101+)",
  "reply.mention_boost": "Boost when user mentions you or says your name",
  "friendship.start_score": "Starting friendship score",
  "friendship.direct_mention_boost": "Boost for direct mentions",
  "friendship.long_chat_boost": "Boost for long conversations",
  "friendship.positive_boost": "Boost for positive interactions",
  "friendship.fact_share_boost": "Boost for sharing facts",
  "friendship.negative_penalty": "Penalty for negative interactions",
  "friendship.weekly_decay": "Weekly decay of friendship score",
  "friendship.friend_threshold": "Score needed to be considered a friend",
  "friendship.bestfriend_threshold": "Score needed to be considered a best friend",
  "friendship.max_abs_score_change_per_day": "Maximum score change per day",
  "memory.max_history_per_channel": "Maximum messages to remember per channel",
  "memory.enable_fact_learning": "Enable learning facts about users",
  "memory.topic_track_max": "Maximum topics to track",
  "memory.fact_decay_days": "Days before facts expire",
  "memory.recall_probability": "Probability of recalling facts",
  "mirror.enable": "Enable style mirroring",
  "mirror.weight_lowercase": "How much to mirror lowercase style",
  "mirror.weight_emoji": "How much to mirror emoji usage",
  "mirror.weight_length": "How much to mirror message length",
  "filters.blocked_user_ids": "List of user IDs to block (one per line)",
  "filters.blocked_keywords": "List of keywords to block (one per line)",
  "filters.require_keyword_any": "Only reply when any of these keywords are present (one per line)",
  "filters.keywords_priority": "Keywords that raise reply priority (one per line)",
  "emoji.reply_emojis": "Emojis to use in reactions (one per line)",
  "emoji.reaction_probability": "Probability of reacting with emojis",
  "emoji.reaction_window_seconds": "Time window for emoji reactions",
  "active_hours.start_hour": "Start of bot's active hours (24-hour format)",
  "active_hours.end_hour": "End of bot's active hours (24-hour format)",
  "self_start.enabled": "Enable self-starting conversations",
  "self_start.min_idle_seconds": "Minimum idle time before self-starting",
  "self_start.chance": "Probability of self-starting a conversation",
  "self_start.openers": "Opening lines for self-started conversations (one per line)",
  "rate_limit.max_per_channel_per_hour": "Maximum messages per channel per hour",
  "rate_limit.per_user_cooldown_s": "Cooldown time per user (seconds)",
  "storage.debug_log_file": "File name for debug logs",
  "storage.ai_log_file": "File name for AI interaction logs",
  "storage.db_file": "Database file name for storing bot data"
};

function fieldFor(key, val, sch) {
  const wrap = document.createElement("div");
  wrap.className = "config-field";
  
  // Create label with description
  const label = document.createElement("div");
  label.className = "config-field-label";
  
  // Get user-friendly label name
  const labelName = key.split('.').pop().replace(/_/g, ' ');
  const displayName = labelName.charAt(0).toUpperCase() + labelName.slice(1);
  
  label.innerHTML = `
    <div class="config-field-name">${displayName}</div>
    ${CONFIG_DESCRIPTIONS[key] ? `<div class="config-field-desc">${CONFIG_DESCRIPTIONS[key]}</div>` : ''}
  `;
  wrap.appendChild(label);
  
  const t = sch.type;
  let inputElement;

  if (t === "boolean") {
    const select = document.createElement("select");
    select.name = key;
    select.className = "form-control form-select";
    select.innerHTML = `
      <option value="true" ${val ? 'selected' : ''}>Enabled</option>
      <option value="false" ${!val ? 'selected' : ''}>Disabled</option>
    `;
    inputElement = select;
  }
  else if (t === "integer" || t === "number") {
    const input = document.createElement("input");
    input.type = "number";
    input.name = key;
    input.className = "form-control";
    input.value = val ?? (t === "integer" ? 0 : 0.0);
    inputElement = input;
  }
  else if (t === "array" && sch.items && sch.items.type === "string") {
    const textarea = document.createElement("textarea");
    textarea.name = key;
    textarea.className = "form-control form-textarea";
    textarea.placeholder = "Enter one item per line";
    textarea.value = (val || []).join("\n");
    inputElement = textarea;
  }
  else if (t === "object") {
    // Special handling for fact_rules object
    if (key === "fact_rules") {
      const textarea = document.createElement("textarea");
      textarea.name = key;
      textarea.className = "form-control form-textarea";
      textarea.placeholder = "Enter regex patterns and their corresponding fact types\nExample:\n\\\\bmy name is\\\\s+([a-zA-Z]+) = name\n\\\\bi am from\\\\s+([a-zA-Z]+) = location";
      textarea.value = Object.entries(val || {}).map(([pattern, type]) => `${pattern} = ${type}`).join("\n");
      inputElement = textarea;
    } else {
      // Handle nested objects like reply.public_probs
      if (typeof val === "object" && val !== null && !Array.isArray(val)) {
        // Create individual inputs for each property in the object
        const objWrap = document.createElement("div");
        objWrap.className = "grid";
        
        for (const [subKey, subVal] of Object.entries(val)) {
          const fullKey = `${key}.${subKey}`;
          const subInput = document.createElement("input");
          subInput.type = typeof subVal === "number" ? "number" : "text";
          subInput.name = fullKey;
          subInput.className = "form-control";
          subInput.value = subVal;
          subInput.placeholder = subKey;
          
          const subLabel = document.createElement("label");
          subLabel.className = "form-label";
          subLabel.textContent = subKey;
          
          const subWrap = document.createElement("div");
          subWrap.className = "form-group";
          subWrap.appendChild(subLabel);
          subWrap.appendChild(subInput);
          
          objWrap.appendChild(subWrap);
        }
        
        inputElement = objWrap;
      } else {
        // Generic object handling
        const textarea = document.createElement("textarea");
        textarea.name = key;
        textarea.className = "form-control form-textarea";
        textarea.placeholder = "Enter JSON object";
        textarea.value = JSON.stringify(val || {}, null, 2);
        inputElement = textarea;
      }
    }
  }
  else {
    const input = document.createElement("input");
    input.name = key;
    input.className = "form-control";
    input.value = val ?? "";
    inputElement = input;
  }
  
  wrap.appendChild(inputElement);
  return wrap;
}

function buildForm(data, sch, prefix = "") {
  const form = document.createDocumentFragment();
  
  // Flatten the configuration object to show each property individually
  function flattenObject(obj, prefix = "") {
    const flattened = [];
    
    for (const [key, value] of Object.entries(obj)) {
      const fullKey = prefix ? `${prefix}.${key}` : key;
      
      if (typeof value === "object" && value !== null && !Array.isArray(value) && !(value instanceof Date)) {
        // For nested objects, check if they're special cases
        if (fullKey === "fact_rules") {
          // Handle fact_rules as a special case
          flattened.push({ key: fullKey, value: value, schema: (sch.properties || {})[key] || { type: "object" } });
        } else {
          // Recursively flatten nested objects
          flattened.push(...flattenObject(value, fullKey));
        }
      } else {
        // Add primitive values and arrays
        flattened.push({ 
          key: fullKey, 
          value: value, 
          schema: getSchemaForPath(sch, fullKey) || { type: typeof value }
        });
      }
    }
    
    return flattened;
  }
  
  // Helper function to get schema for a specific path
  function getSchemaForPath(schema, path) {
    const parts = path.split('.');
    let current = schema;
    
    for (const part of parts) {
      if (current && current.properties && current.properties[part]) {
        current = current.properties[part];
      } else {
        return null;
      }
    }
    
    return current;
  }
  
  // Flatten the configuration data
  const flatConfig = flattenObject(data, prefix);
  
  // Create property fields
  flatConfig.forEach(({ key, value, schema }) => {
    const field = fieldFor(key, value, schema);
    form.appendChild(field);
  });
  
  return form;
}

function setDeep(obj, path, value){
  const keys = path.split(".");
  let cur = obj;
  keys.forEach((k, i)=>{
    if (i===keys.length-1) {
      // For the final key, set the value directly
      cur[k] = value;
    }
    else { 
      // For intermediate keys, create objects if they don't exist
      cur[k] = cur[k] ?? {}; 
      cur = cur[k]; 
    }
  });
}

function readForm() {
  const out = JSON.parse(JSON.stringify(config||{}));
  document.querySelectorAll("#cfgForm [name]").forEach(el=>{
    const path = el.name;
    const parts = path.split(".");
    let sch = schema;
    for (const p of parts){
      if (!sch || sch.type!=="object") { sch = {type:"string"}; break; }
      sch = sch.properties?.[p];
    }
    const t = sch?.type || "string";
    let v = el.value;
    
    // Special handling for fact_rules
    if (path === "fact_rules") {
      try {
        const lines = v.split("\n").filter(line => line.trim() !== "");
        const rules = {};
        lines.forEach(line => {
          const match = line.match(/^(.+?)\s*=\s*(.+)$/);
          if (match) {
            rules[match[1].trim()] = match[2].trim();
          }
        });
        v = rules;
      } catch (e) {
        console.error("Error parsing fact rules", e);
        v = {};
      }
    }
    // Special handling for array-like textareas
    else if (t==="array" && sch.items?.type==="string") {
      v = String(v).split("\n").map(s=>s.trim()).filter(Boolean);
    }
    // Special handling for nested objects like reply.public_probs
    else if (path.includes(".") && !path.startsWith("reply.public_probs")) {
      // This is a nested property, set it directly
      setDeep(out, path, v);
      return; // Skip the regular setDeep call
    }
    else if (t==="boolean") v = String(v).toLowerCase()==="true";
    else if (t==="integer") v = Number(v||0);
    else if (t==="number") v = Number(v||0);
    else if (t==="object") { 
      try{ 
        // Check if this is a special nested object
        if (path.startsWith("reply.public_probs")) {
          // For public_probs, we need to parse the individual properties
          // These are handled as individual inputs, so we don't need to parse them here
          return; // Skip setting this as it's handled individually
        } else {
          v = JSON.parse(v||"{}"); 
        }
      } catch(_){ 
        v = {}; 
      }
    }
    else v = String(v);
    
    // For nested properties, set them directly
    if (path.includes(".")) {
      setDeep(out, path, v);
    } else {
      // For top-level properties, use the regular approach
      setDeep(out, path, v);
    }
  });
  return out;
}

async function loadConfig(){
  try {
    const r = await fetchJSON(`/api/bots/${botId}/config`);
    config = r.config || {}; 
    schema = r.schema || {type:"object",properties:{}};
    const form = $("#cfgForm"); 
    form.innerHTML = "";
    form.appendChild(buildForm(config, schema));
  } catch (error) {
    console.error("Error loading config", error);
    alert("Error loading configuration: " + error.message);
  }
}

// Tab switching
document.addEventListener("click", (e)=>{
  const b = e.target.closest(".tab-btn"); 
  if (!b) return;
  
  // Update active tab button
  document.querySelectorAll(".tab-btn").forEach(x=>x.classList.remove("active"));
  b.classList.add("active");
  
  // Show active tab content
  document.querySelectorAll(".tab-content").forEach(el=>el.classList.remove("active"));
  document.querySelector(`#tab-${b.dataset.tab}`).classList.add("active");
  
  // Special handling for logs tab
  if (b.dataset.tab==="logs") {
    openLogWS();
  }
});

// Save config
$("#saveCfg").onclick = async ()=>{
  try {
    const payload = readForm();
    const response = await fetch("/api/bots/"+botId+"/config", {
      method:"PUT",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    alert("Configuration saved successfully!");
  } catch (error) {
    console.error("Error saving config", error);
    alert("Error saving configuration: " + error.message);
  }
};

// Clear logs
$("#clearLogs").onclick = ()=>{
  const logBox = $("#logbox");
  logBox.textContent = "";
  logBox.scrollTop = 0;
};

// Initialize
openStatusWS();
loadConfig();