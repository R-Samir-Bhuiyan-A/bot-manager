// app/static/dashboard.js
const $ = s => document.querySelector(s);
let ws = null, bots = [];

function badge(s){
  if (s==="running") return '<span class="bot-status running"><i class="fas fa-circle"></i> running</span>';
  if (s==="stopped") return '<span class="bot-status stopped"><i class="fas fa-circle"></i> stopped</span>';
  return `<span class="bot-status error"><i class="fas fa-exclamation-circle"></i> ${s}</span>`;
}

function render() {
  const wrap = $("#cards");
  const emptyState = $("#empty-state");
  const botCount = $("#bot-count");
  
  // Update bot count
  botCount.textContent = `${bots.length} ${bots.length === 1 ? 'bot' : 'bots'}`;
  
  if (bots.length === 0) {
    wrap.style.display = "none";
    emptyState.style.display = "block";
    return;
  }
  
  wrap.style.display = "grid";
  emptyState.style.display = "none";
  wrap.innerHTML = "";
  
  bots.forEach(b => {
    const el = document.createElement("div");
    el.className = "bot-card";
    el.innerHTML = `
      <div class="bot-header">
        <h3 class="bot-name">${b.name}</h3>
        ${badge(b.status)}
      </div>
      
      <div class="bot-stats">
        <div class="stat-item">
          <div class="stat-label">CPU</div>
          <div class="stat-value">${b.cpu}%</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">RAM</div>
          <div class="stat-value">${b.memory_mb} MB</div>
        </div>
      </div>
      
      <div class="bot-actions">
        <a class="btn btn-secondary btn-sm" href="/ui/bot.html?id=${encodeURIComponent(b.id)}">
          <i class="fas fa-cog"></i>
        </a>
        <button class="btn ${b.status === 'running' ? 'btn-secondary' : 'btn-success'} btn-sm" onclick="toggleBot('${b.id}', '${b.status}')">
          ${b.status === 'running' ? '<i class="fas fa-stop"></i>' : '<i class="fas fa-play"></i>'}
        </button>
        <button class="btn btn-secondary btn-sm" onclick="restartBot('${b.id}')">
          <i class="fas fa-redo"></i>
        </button>
        <button class="btn btn-danger btn-sm" onclick="delBot('${b.id}')">
          <i class="fas fa-trash"></i>
        </button>
      </div>
    `;
    wrap.appendChild(el);
  });
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

async function toggleBot(id, status) {
  if (status === "running") {
    await post(`/api/bots/${id}/stop`);
  } else {
    await post(`/api/bots/${id}/start`);
  }
}

async function restartBot(id) {
  await post(`/api/bots/${id}/restart`);
}

async function delBot(id){
  if (!confirm(`Are you sure you want to delete bot ${id}?`)) return;
  try {
    const response = await fetch(`/api/bots/${id}`, {method:"DELETE"});
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
  } catch (error) {
    console.error("Error deleting bot", id, error);
    alert("Error deleting bot: " + error.message);
  }
}

function connect(){
  if (ws) ws.close();
  ws = new WebSocket(`${location.origin.replace("http","ws")}/ws/status`);
  ws.onmessage = ev => { 
    try {
      bots = JSON.parse(ev.data); 
      render(); 
    } catch (error) {
      console.error("Error parsing WebSocket message", error);
    }
  };
  ws.onclose = () => setTimeout(connect, 1500);
  ws.onerror = (error) => console.error("WebSocket error", error);
}
connect();

$("#btn-create").onclick = ()=> $("#createDlg").showModal();
$("#cancelCreate").onclick = ()=> $("#createDlg").close();
$("#cancelCreateFooter").onclick = ()=> $("#createDlg").close();

$("#okCreate").onclick = async ()=>{
  const name = $("#newName").value.trim() || "Bot";
  try {
    const response = await fetch("/api/bots", {
      method:"POST", 
      headers:{"Content-Type":"application/json"}, 
      body: JSON.stringify({name})
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    $("#newName").value = "";
    $("#createDlg").close();
  } catch (error) {
    console.error("Error creating bot", error);
    alert("Error creating bot: " + error.message);
  }
};

// Close dialog when clicking on backdrop
document.addEventListener('click', (e) => {
  const dialog = $("#createDlg");
  if (dialog && dialog.open && e.target === dialog) {
    dialog.close();
  }
});