const DEMO_PATIENT_ID = 1;
const TOKEN_KEY = "sahalink.token";
let currentUser = null;
let currentView = "doctor";
let eventsSocket;
let activeConsultation = null;
let localStream;
let peerConnection;
let signalSocket;
let toastTimer;

const ICON_ALERT_TRIANGLE = '<svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4 2.5 20h19L12 4Z"></path><path d="M12 10.5v4"></path><path d="M12 17.2h.01"></path></svg>';
const ICON_CHECK_CIRCLE = '<svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8.5"></circle><path d="M8.5 12.3 11 14.8 15.5 9.5"></path></svg>';
const ICON_CLOCK_SM = '<svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8.5"></circle><path d="M12 7.5V12l3 2"></path></svg>';

const $ = (selector) => document.querySelector(selector);

// Per-tab storage: a doctor and a patient can be logged in side by side in one browser.
function readToken() {
  try { return sessionStorage.getItem(TOKEN_KEY) || ""; } catch { return ""; }
}

function storeToken(token) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch { /* storage unavailable: the session lasts until the tab reloads */ }
}

let authToken = readToken();

const api = async (path, options = {}) => {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401 && currentUser) {
    handleSessionExpired();
    throw new Error("Session expiree. Veuillez vous reconnecter.");
  }
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || "Une erreur est survenue.");
  }
  return response.status === 204 ? null : response.json();
};

const isDoctor = () => currentUser?.role === "doctor";
const currentPatientId = () => (currentUser?.role === "patient" ? currentUser.patient_id : DEMO_PATIENT_ID);
const socketUrl = (path) => `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}${path}`;

function initials(name) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0].toUpperCase()).join("");
}

function toast(message, error = false) {
  const element = $("#toast");
  element.textContent = message;
  element.classList.toggle("error", error);
  element.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => element.classList.remove("show"), 3200);
}

function formatDate(value) {
  return new Intl.DateTimeFormat("fr-MA", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function canSee(view) {
  const navItem = document.querySelector(`.nav-item[data-view="${view}"]`);
  return Boolean(currentUser && navItem && navItem.dataset.roles.split(" ").includes(currentUser.role));
}

function showView(name) {
  if (!canSee(name)) return;
  currentView = name;
  document.querySelectorAll(".view").forEach((element) => element.classList.toggle("active", element.id === `${name}-view`));
  document.querySelectorAll(".nav-item").forEach((element) => element.classList.toggle("active", element.dataset.view === name));
  const labels = {
    doctor: ["ESPACE MEDECIN", `Bonjour, ${currentUser.display_name}`],
    patient: ["ESPACE PATIENT", "Mon suivi"],
    video: ["TELECONSULTATION", "Salle de consultation"],
  };
  $("#view-kicker").textContent = labels[name][0];
  $("#view-title").textContent = labels[name][1];
  $(".sidebar").classList.remove("open");
  if (name === "doctor") refreshDashboard();
  if (name === "patient") refreshPatientView();
  if (name === "video") refreshConsultation();
}

function showLoginScreen() {
  $(".app-shell").hidden = true;
  $("#login-screen").hidden = false;
  $("#login-password").value = "";
  $("#login-username").focus();
}

function applyRole() {
  document.querySelectorAll("[data-roles]").forEach((element) => {
    element.hidden = !element.dataset.roles.split(" ").includes(currentUser.role);
  });
  const avatar = $("#user-avatar");
  avatar.textContent = initials(currentUser.display_name);
  avatar.setAttribute("aria-label", `Profil ${currentUser.display_name}`);
  $("#patient-heading").textContent = `Bonjour ${currentUser.display_name.split(" ")[0]}`;
  $("#remote-placeholder-hint").textContent = isDoctor()
    ? "Le patient apparaitra ici des qu'il rejoint la consultation."
    : "Votre medecin apparaitra ici.";
}

async function startSession(user) {
  currentUser = user;
  $("#login-screen").hidden = true;
  $(".app-shell").hidden = false;
  applyRole();
  updateConsultationUi();
  connectEvents();
  refreshCameraList();
  showView(isDoctor() ? "doctor" : "patient");
  await refreshConsultation();
}

function resetSessionState() {
  if (localStream) endCall({ notifyServer: false });
  currentUser = null;
  activeConsultation = null;
  authToken = "";
  storeToken("");
  const socket = eventsSocket;
  eventsSocket = null;
  socket?.close();
  $("#invite-banner").hidden = true;
}

function handleSessionExpired() {
  resetSessionState();
  showLoginScreen();
  $("#login-error").textContent = "Votre session a expire. Veuillez vous reconnecter.";
}

async function submitLogin(event) {
  event.preventDefault();
  const username = $("#login-username").value.trim();
  const password = $("#login-password").value;
  const error = $("#login-error");
  if (!username || !password) { error.textContent = "Saisissez votre identifiant et votre mot de passe."; return; }
  const button = $("#login-submit");
  button.disabled = true;
  error.textContent = "";
  try {
    const session = await api("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
    authToken = session.token;
    storeToken(session.token);
    await startSession(session.user);
  } catch (loginError) {
    error.textContent = loginError.message;
  } finally {
    button.disabled = false;
  }
}

async function logout() {
  const token = authToken;
  resetSessionState();
  showLoginScreen();
  $("#login-error").textContent = "";
  if (token) fetch("/api/auth/logout", { method: "POST", headers: { Authorization: `Bearer ${token}` } }).catch(() => {});
}

async function restoreSession() {
  if (!authToken) { showLoginScreen(); return; }
  try {
    const response = await fetch("/api/auth/me", { headers: { Authorization: `Bearer ${authToken}` } });
    if (!response.ok) throw new Error("expired");
    await startSession(await response.json());
  } catch {
    authToken = "";
    storeToken("");
    showLoginScreen();
  }
}

function vitalMarkup(vital) {
  if (!vital) return ["--", "--", "--", "--"];
  return [`${vital.systolic}/${vital.diastolic}`, vital.heart_rate, vital.spo2, vital.temperature];
}

function updateVitalCards(vital) {
  const values = vitalMarkup(vital);
  document.querySelectorAll("#doctor-vitals .vital-card strong").forEach((element, index) => element.textContent = values[index]);
  $("#last-reading-time").textContent = vital ? formatDate(vital.recorded_at).split(" ").slice(-1)[0] : "Aucune";
}

function rowMarkup(vital, includeSource = true) {
  const sourceCell = includeSource
    ? `<td><span class="source-pill ${vital.source}">${vital.source === "simulated" ? "Simulee" : "Saisie patient"}</span></td>`
    : "";
  return `<tr><td>${formatDate(vital.recorded_at)}</td><td>${vital.systolic}/${vital.diastolic} mmHg</td><td>${vital.heart_rate} bpm</td><td>${vital.spo2}%</td><td>${vital.temperature} deg C</td>${sourceCell}</tr>`;
}

async function refreshHistory() {
  const vitals = await api(`/api/patients/${currentPatientId()}/vitals`);
  $("#doctor-history").innerHTML = vitals.length ? vitals.map((item) => rowMarkup(item)).join("") : `<tr><td colspan="6">Aucune constante enregistree.</td></tr>`;
  $("#patient-history").innerHTML = vitals.length ? vitals.map((item) => rowMarkup(item, false)).join("") : `<tr><td colspan="5">Aucune constante enregistree.</td></tr>`;
  updateVitalCards(vitals[0]);
}

function showConsentState(consent) {
  const accepted = Boolean(consent?.accepted);
  const badge = $("#consent-badge");
  badge.textContent = accepted ? "Confirme" : "A confirmer";
  badge.className = accepted ? "tag" : "tag neutral";
  $("#consent-check").checked = accepted;
}

async function refreshPatientView() {
  try {
    const [patient] = await Promise.all([api(`/api/patients/${currentPatientId()}`), refreshHistory()]);
    showConsentState(patient.latest_consent);
  } catch (error) { toast(error.message, true); }
}

function alertMarkup(alert) {
  const severity = alert.severity === "critical" ? "critical" : "";
  const action = alert.status === "open"
    ? `<button type="button" data-alert-id="${alert.id}" class="acknowledge">${ICON_CHECK_CIRCLE}<span>Acquitter l'alerte</span></button>`
    : `<span class="alert-done">${ICON_CHECK_CIRCLE}<span>Alerte acquittee</span></span>`;
  return `<article class="alert-item ${severity}">
    <div class="alert-item-head">
      <span class="alert-icon" aria-hidden="true">${ICON_ALERT_TRIANGLE}</span>
      <strong>${alert.patient_name}</strong>
      <span class="severity-pill">${alert.severity === "critical" ? "Critique" : "A surveiller"}</span>
    </div>
    <p>${alert.message}</p>
    <div class="alert-item-foot">
      <span class="alert-time">${ICON_CLOCK_SM}<span>${formatDate(alert.created_at)}</span></span>
      ${action}
    </div>
  </article>`;
}

async function refreshAlerts() {
  const alerts = await api("/api/alerts");
  const open = alerts.filter((alert) => alert.status === "open");
  $("#alert-count").textContent = open.length;
  $("#open-alerts").textContent = open.length.toString().padStart(2, "0");
  $("#alerts-list").innerHTML = alerts.length ? alerts.map(alertMarkup).join("") : `<p class="empty-state">Aucune alerte ouverte. Les seuils sont surveilles en continu.</p>`;
}

async function refreshDashboard() {
  if (!isDoctor()) return;
  try {
    const dashboard = await api("/api/dashboard");
    updateVitalCards(dashboard.latest_vital);
    $("#consent-state").textContent = dashboard.latest_consent?.accepted ? "Confirme" : "En attente";
    await Promise.all([refreshHistory(), refreshAlerts()]);
  } catch (error) { toast(`Chargement impossible : ${error.message}`, true); }
}

async function submitVital(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = Object.fromEntries(form.entries());
  Object.keys(payload).forEach((key) => payload[key] = Number(payload[key]));
  try {
    const result = await api(`/api/patients/${currentPatientId()}/vitals`, { method: "POST", body: JSON.stringify(payload) });
    const feedback = result.alert ? `Mesure enregistree. Alerte transmise a votre medecin : ${result.alert.message}.` : "Mesure enregistree et transmise au medecin.";
    $("#vital-feedback").textContent = feedback;
    toast(result.alert ? "Alerte clinique envoyee a votre medecin." : "Constantes envoyees.", Boolean(result.alert));
    await refreshHistory();
  } catch (error) { $("#vital-feedback").textContent = error.message; toast(error.message, true); }
}

async function submitConsent(event) {
  event.preventDefault();
  try {
    const consent = await api(`/api/patients/${currentPatientId()}/consents`, { method: "POST", body: JSON.stringify({ accepted: $("#consent-check").checked, purpose: "Teleconsultation pedagogique et suivi des constantes simulees." }) });
    showConsentState(consent);
    $("#consent-feedback").textContent = "Votre consentement a ete enregistre avec horodatage.";
    toast("Consentement enregistre.");
  } catch (error) { $("#consent-feedback").textContent = error.message; toast(error.message, true); }
}

async function acknowledgeAlert(id) {
  try { await api(`/api/alerts/${id}/acknowledge`, { method: "PATCH" }); toast("Alerte acquittee."); refreshAlerts(); } catch (error) { toast(error.message, true); }
}

function connectEvents() {
  const socket = new WebSocket(socketUrl("/ws/events"));
  eventsSocket = socket;
  socket.onopen = () => socket.send(JSON.stringify({ type: "auth", token: authToken }));
  socket.onmessage = (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "auth-failed") { handleSessionExpired(); return; }
    if (payload.type === "alert") {
      toast(`Nouvelle alerte : ${payload.alert.message}`, true);
      refreshDashboard();
    }
    if (payload.type === "invitation") {
      activeConsultation = payload.consultation;
      toast(`${activeConsultation.doctor_name} vous invite en teleconsultation.`);
      updateConsultationUi();
    }
    if (payload.type === "consultation-ended") {
      activeConsultation = null;
      if (localStream) endCall({ notifyServer: false });
      setVideoStatus("Le medecin a termine la consultation.");
      updateConsultationUi();
    }
  };
  socket.onclose = () => {
    if (eventsSocket === socket && currentUser) setTimeout(() => { if (eventsSocket === socket && currentUser) connectEvents(); }, 2500);
  };
}

function updateConsultationUi() {
  if (!currentUser) return;
  const inCall = Boolean(localStream);
  const banner = $("#invite-banner");
  banner.hidden = isDoctor() || !activeConsultation || inCall;
  if (activeConsultation) $("#invite-title").textContent = `${activeConsultation.doctor_name} vous invite en teleconsultation`;

  const info = $("#consultation-info");
  const startButton = $("#start-call");
  const startLabel = $("#start-call-label");
  if (isDoctor()) {
    info.textContent = activeConsultation
      ? `Consultation ouverte avec ${activeConsultation.patient_name}.`
      : "Patient : Amal El Idrissi. Le patient recevra une invitation des que vous demarrez.";
    startLabel.textContent = activeConsultation ? "Rejoindre la consultation" : "Demarrer la consultation";
    startButton.disabled = inCall;
  } else {
    info.textContent = activeConsultation
      ? `${activeConsultation.doctor_name} vous attend dans la salle de teleconsultation.`
      : "Aucune consultation en cours. Votre medecin vous enverra une invitation.";
    startLabel.textContent = "Rejoindre la consultation";
    startButton.disabled = inCall || !activeConsultation;
  }
  if (inCall) startLabel.textContent = "Consultation en cours";
}

async function refreshConsultation() {
  if (!currentUser) return;
  try {
    activeConsultation = await api("/api/consultations/active");
  } catch { /* keep the last known state; the next event or view change refreshes it */ }
  updateConsultationUi();
}

async function joinFromPatientSide() {
  if (!activeConsultation) await refreshConsultation();
  if (!activeConsultation) { toast("Aucune consultation en cours. Attendez l'invitation de votre medecin.", true); return; }
  showView("video");
  activateVideo();
}

// Phone-as-webcam drivers (Camo, Iriun, OBS...) output black or a logo when idle, so never prefer them.
const VIRTUAL_DEVICE_PATTERN = /camo|iriun|droidcam|epoccam|manycam|snap camera|xsplit|nvidia broadcast|mmhmm|vmix|\bndi\b|\bobs\b|virtual|e2esoft|splitcam|youcam|avatarify|fake/i;
const INFRARED_CAMERA_PATTERN = /\bir\b|infrared|depth|windows hello/i;
const PHYSICAL_CAMERA_PATTERN = /webcam|uvc|integrated|hd camera|facetime|usb/i;
const BLACK_FRAME_LUMINANCE = 6;
const CAMERA_PREFERENCE_KEY = "sahalink.cameraId";
const clientId = Math.random().toString(36).slice(2);
let signalQueue = Promise.resolve();
let pendingCandidates = [];
let activeCameraLabel = "";
let remoteConnected = false;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const setVideoStatus = (text) => { $("#video-status").textContent = text; };

function readCameraPreference() {
  try { return localStorage.getItem(CAMERA_PREFERENCE_KEY) || ""; } catch { return ""; }
}

function saveCameraPreference(deviceId) {
  try {
    if (deviceId) localStorage.setItem(CAMERA_PREFERENCE_KEY, deviceId);
    else localStorage.removeItem(CAMERA_PREFERENCE_KEY);
  } catch { /* storage unavailable: the preference simply is not remembered */ }
}

function cameraScore(device) {
  const label = device.label || "";
  if (INFRARED_CAMERA_PATTERN.test(label)) return 0;
  if (VIRTUAL_DEVICE_PATTERN.test(label)) return 1;
  return PHYSICAL_CAMERA_PATTERN.test(label) ? 3 : 2;
}

async function listDevices(kind) {
  let devices = await navigator.mediaDevices.enumerateDevices();
  if (!devices.some((device) => device.kind === kind && device.label)) {
    // Labels stay hidden until the page holds a permission, so ask once and release immediately.
    const permission = await navigator.mediaDevices.getUserMedia(kind === "videoinput" ? { video: true } : { audio: true });
    permission.getTracks().forEach((track) => track.stop());
    devices = await navigator.mediaDevices.enumerateDevices();
  }
  return devices.filter((device) => device.kind === kind && device.deviceId);
}

function averageLuminance(source, width, height) {
  if (!width || !height) return null;
  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 48;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  try {
    ctx.drawImage(source, 0, 0, canvas.width, canvas.height);
    const { data } = ctx.getImageData(0, 0, canvas.width, canvas.height);
    let total = 0;
    for (let i = 0; i < data.length; i += 4) total += (data[i] + data[i + 1] + data[i + 2]) / 3;
    return Math.round(total / (data.length / 4));
  } catch {
    return null;
  }
}

async function frameLuminance(track, timeoutMs, fallbackVideo) {
  if (typeof ImageCapture === "function") {
    try {
      const bitmap = await Promise.race([new ImageCapture(track).grabFrame(), sleep(timeoutMs).then(() => null)]);
      if (!bitmap) return null;
      const value = averageLuminance(bitmap, bitmap.width, bitmap.height);
      bitmap.close?.();
      return value;
    } catch { /* grabFrame unsupported for this track: read it through the video element instead */ }
  }
  if (fallbackVideo.srcObject?.getVideoTracks?.()[0] !== track) {
    fallbackVideo.srcObject = new MediaStream([track]);
    fallbackVideo.play?.().catch(() => {});
  }
  const deadline = performance.now() + timeoutMs;
  while (performance.now() < deadline) {
    const value = averageLuminance(fallbackVideo, fallbackVideo.videoWidth, fallbackVideo.videoHeight);
    if (value !== null) return value;
    await sleep(100);
  }
  return null;
}

// Webcams can take seconds to deliver a first frame, which is dark until auto-exposure settles.
async function peakLuminance(track, fallbackVideo, { firstFrameTimeoutMs = 6000, settleMs = 2000 } = {}) {
  let peak = await frameLuminance(track, firstFrameTimeoutMs, fallbackVideo);
  if (peak === null) return null;
  const settleEnd = performance.now() + settleMs;
  while (peak <= BLACK_FRAME_LUMINANCE * 3 && performance.now() < settleEnd) {
    await sleep(250);
    const value = await frameLuminance(track, 1000, fallbackVideo);
    if (value !== null) peak = Math.max(peak, value);
  }
  return peak;
}

const isBlack = (luminance) => luminance === null || luminance <= BLACK_FRAME_LUMINANCE;

function openCamera(deviceId) {
  return navigator.mediaDevices.getUserMedia({
    video: { deviceId: { exact: deviceId }, width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 24 } },
  });
}

async function findWorkingCamera() {
  const cameras = await listDevices("videoinput");
  if (!cameras.length) throw new Error("Aucune camera detectee.");
  const preferred = readCameraPreference();
  const ordered = [...cameras].sort((a, b) => (b.deviceId === preferred) - (a.deviceId === preferred) || cameraScore(b) - cameraScore(a));
  let fallback = null;
  for (const camera of ordered) {
    setVideoStatus(`Test de la camera : ${camera.label || "camera par defaut"}...`);
    let stream;
    try { stream = await openCamera(camera.deviceId); } catch { continue; }
    const luminance = await peakLuminance(stream.getVideoTracks()[0], $("#local-video"));
    if (!isBlack(luminance)) {
      fallback?.stream.getTracks().forEach((track) => track.stop());
      return { stream, camera, luminance };
    }
    if (fallback) stream.getTracks().forEach((track) => track.stop());
    else fallback = { stream, camera, luminance };
  }
  if (fallback) return fallback;
  throw new Error("Aucune camera n'a pu etre ouverte.");
}

async function openMicrophone() {
  try {
    const microphones = await listDevices("audioinput");
    const real = microphones.find((mic) => mic.deviceId === "default" && !VIRTUAL_DEVICE_PATTERN.test(mic.label))
      || microphones.find((mic) => mic.deviceId !== "default" && mic.deviceId !== "communications" && !VIRTUAL_DEVICE_PATTERN.test(mic.label));
    const audio = real ? { deviceId: { exact: real.deviceId }, echoCancellation: true, noiseSuppression: true } : true;
    return await navigator.mediaDevices.getUserMedia({ audio });
  } catch {
    try { return await navigator.mediaDevices.getUserMedia({ audio: true }); } catch { return null; }
  }
}

async function refreshCameraList() {
  const select = $("#camera-select");
  let cameras = [];
  try {
    cameras = (await navigator.mediaDevices.enumerateDevices()).filter((device) => device.kind === "videoinput" && device.deviceId);
  } catch { return; }
  const current = localStream?.getVideoTracks()[0]?.getSettings().deviceId || readCameraPreference();
  select.replaceChildren(new Option("Detection automatique", ""));
  cameras.forEach((camera, index) => {
    const name = camera.label || `Camera ${index + 1}`;
    const virtual = camera.label && cameraScore(camera) < 2;
    select.add(new Option(virtual ? `${name} (virtuelle)` : name, camera.deviceId));
  });
  select.value = cameras.some((camera) => camera.deviceId === current) ? current : "";
}

function connectionSummary() {
  return remoteConnected ? "Consultation connectee." : "En attente d'un correspondant dans la salle...";
}

function reportCameraHealth(luminance) {
  if (isBlack(luminance)) {
    setVideoStatus(`Camera : ${activeCameraLabel}. Elle n'envoie qu'une image noire : choisissez une autre camera dans la liste. ${connectionSummary()}`);
    toast("La camera choisie n'envoie qu'une image noire.", true);
    return;
  }
  const virtualHint = cameraScore({ label: activeCameraLabel }) < 2
    ? " Camera virtuelle : si l'image ne vous correspond pas, choisissez votre webcam dans la liste."
    : "";
  setVideoStatus(`Camera : ${activeCameraLabel}.${virtualHint} ${connectionSummary()}`);
}

function attachLocalPreview() {
  const localVideo = $("#local-video");
  localVideo.srcObject = null;
  localVideo.srcObject = localStream;
  localVideo.play?.().catch(() => {});
}

function watchTrackEnd(track) {
  track.onended = () => {
    if (track.kind === "video") toast("La camera a ete deconnectee. Choisissez une autre camera dans la liste.", true);
    else toast("Le microphone a ete deconnecte.", true);
    refreshCameraList();
  };
}

async function ensureConsultation() {
  if (!activeConsultation) await refreshConsultation();
  if (activeConsultation) return activeConsultation;
  if (!isDoctor()) throw new Error("Aucune consultation en cours. Attendez l'invitation de votre medecin.");
  activeConsultation = await api("/api/consultations", { method: "POST", body: JSON.stringify({ patient_id: DEMO_PATIENT_ID }) });
  toast(`Invitation envoyee a ${activeConsultation.patient_name}.`);
  return activeConsultation;
}

async function activateVideo() {
  if (localStream) { toast("La camera est deja active. Utilisez la liste des cameras pour en changer.", true); return; }
  const startButton = $("#start-call");
  startButton.disabled = true;
  let consultation;
  try {
    consultation = await ensureConsultation();
  } catch (error) {
    setVideoStatus(error.message);
    toast(error.message, true);
    updateConsultationUi();
    return;
  }
  updateConsultationUi();
  startButton.disabled = true;
  setVideoStatus("Recherche d'une camera qui fournit une image...");
  try {
    const selected = await findWorkingCamera();
    const microphone = await openMicrophone();
    localStream = new MediaStream([...selected.stream.getVideoTracks(), ...(microphone ? microphone.getAudioTracks() : [])]);
    localStream.getTracks().forEach(watchTrackEnd);
    activeCameraLabel = selected.camera.label || "camera par defaut";
    if (!isBlack(selected.luminance) && cameraScore(selected.camera) >= 2) saveCameraPreference(selected.camera.deviceId);
    attachLocalPreview();
    await refreshCameraList();
    if (!microphone) toast("Microphone indisponible : la consultation continue sans son.", true);
    reportCameraHealth(selected.luminance);
    connectSignaling(consultation.room);
  } catch (error) {
    localStream?.getTracks().forEach((track) => track.stop());
    localStream = null;
    setVideoStatus("Camera indisponible. Autorisez l'acces a la camera dans le navigateur puis reessayez.");
    toast("Impossible d'acceder a la camera.", true);
  } finally {
    updateConsultationUi();
  }
}

async function switchCamera(deviceId) {
  if (!deviceId) {
    saveCameraPreference("");
    toast("Detection automatique de la camera activee.");
    return;
  }
  saveCameraPreference(deviceId);
  if (!localStream) { toast("Camera enregistree pour la prochaine consultation."); return; }
  try {
    const freshTrack = (await openCamera(deviceId)).getVideoTracks()[0];
    const oldTrack = localStream.getVideoTracks()[0];
    if (oldTrack) {
      freshTrack.enabled = oldTrack.enabled;
      localStream.removeTrack(oldTrack);
      oldTrack.stop();
    }
    localStream.addTrack(freshTrack);
    watchTrackEnd(freshTrack);
    const sender = peerConnection?.getSenders().find((item) => item.track?.kind === "video");
    if (sender) await sender.replaceTrack(freshTrack);
    else if (peerConnection) peerConnection.addTrack(freshTrack, localStream);
    attachLocalPreview();
    activeCameraLabel = freshTrack.label || "camera selectionnee";
    sendSignal({ type: "camera-state", enabled: freshTrack.enabled });
    reportCameraHealth(await peakLuminance(freshTrack, $("#local-video")));
  } catch {
    toast("Impossible d'ouvrir cette camera : elle est peut-etre utilisee par une autre application.", true);
    refreshCameraList();
  }
}

function sendSignal(message) {
  if (signalSocket?.readyState === WebSocket.OPEN) signalSocket.send(JSON.stringify({ ...message, from: clientId }));
}

function connectSignaling(room) {
  signalSocket = new WebSocket(socketUrl(`/ws/signaling/${encodeURIComponent(room)}`));
  const socket = signalSocket;
  socket.onopen = () => socket.send(JSON.stringify({ type: "auth", token: authToken }));
  // Apply signaling strictly in order: a candidate handled before its offer is silently dropped.
  socket.onmessage = (event) => {
    signalQueue = signalQueue.then(() => handleSignal(JSON.parse(event.data))).catch(() => {});
  };
  socket.onclose = () => {
    if (socket === signalSocket && localStream) setVideoStatus("Signalisation deconnectee. Cliquez sur Terminer puis rejoignez a nouveau la consultation.");
  };
}

function resetRemoteVideo() {
  $("#remote-video").srcObject = null;
  $("#remote-placeholder").hidden = false;
}

function createPeerConnection() {
  peerConnection?.close();
  pendingCandidates = [];
  remoteConnected = false;
  const pc = new RTCPeerConnection({ iceServers: [{ urls: "stun:stun.l.google.com:19302" }] });
  localStream.getTracks().forEach((track) => pc.addTrack(track, localStream));
  pc.onicecandidate = (event) => { if (event.candidate) sendSignal({ type: "candidate", candidate: event.candidate }); };
  pc.ontrack = (event) => {
    const remoteVideo = $("#remote-video");
    if (remoteVideo.srcObject !== event.streams[0]) {
      remoteVideo.srcObject = event.streams[0];
      remoteVideo.play?.().catch(() => { remoteVideo.muted = true; remoteVideo.play?.().catch(() => {}); });
    }
    $("#remote-placeholder").hidden = true;
  };
  pc.onconnectionstatechange = () => {
    if (pc !== peerConnection) return;
    if (pc.connectionState === "connected") {
      remoteConnected = true;
      setVideoStatus(`Consultation connectee. Camera : ${activeCameraLabel}.`);
      checkRemoteImage(pc);
    } else if (pc.connectionState === "disconnected") {
      setVideoStatus("Connexion instable avec le correspondant, reconnexion en cours...");
    } else if (pc.connectionState === "failed") {
      remoteConnected = false;
      resetRemoteVideo();
      setVideoStatus("Connexion perdue avec le correspondant. Il peut rejoindre a nouveau la salle.");
    }
  };
  peerConnection = pc;
  return pc;
}

async function checkRemoteImage(pc) {
  await sleep(3000);
  if (pc !== peerConnection || pc.connectionState !== "connected") return;
  const remoteVideo = $("#remote-video");
  const remoteTrack = remoteVideo.srcObject?.getVideoTracks?.()[0];
  if (!remoteTrack) return;
  const peak = await peakLuminance(remoteTrack, remoteVideo, { firstFrameTimeoutMs: 4000, settleMs: 2000 });
  if (pc !== peerConnection) return;
  if (isBlack(peak)) {
    setVideoStatus(`Consultation connectee, mais le correspondant n'envoie qu'une image noire (camera coupee ou camera virtuelle selectionnee de son cote). Votre camera : ${activeCameraLabel}.`);
  } else {
    setVideoStatus(`Consultation connectee. Camera : ${activeCameraLabel}.`);
  }
}

async function flushPendingCandidates(pc) {
  const queued = pendingCandidates;
  pendingCandidates = [];
  for (const candidate of queued) await pc.addIceCandidate(candidate).catch(() => {});
}

async function handleSignal(message) {
  if (!message?.type || !localStream) return;
  if (message.type === "auth-ok") {
    createPeerConnection();
    setVideoStatus(`Camera : ${activeCameraLabel}. En attente de ${isDoctor() ? "votre patient" : "votre medecin"} dans la salle...`);
    sendSignal({ type: "join" });
    return;
  }
  if (message.type === "auth-failed") {
    handleSessionExpired();
    return;
  }
  if (message.type === "forbidden") {
    endCall({ notifyServer: false });
    setVideoStatus("Cette consultation est terminee ou ne vous est pas destinee.");
    refreshConsultation();
    return;
  }
  if (message.type === "room-full") {
    endCall({ notifyServer: false });
    setVideoStatus("Vous etes deja connecte a cette consultation dans un autre onglet ou une autre fenetre.");
    return;
  }
  if (!peerConnection) return;
  if (message.type === "join") {
    // The peer already in the room makes the offer, so the newcomer never offers into an empty room.
    const pc = createPeerConnection();
    resetRemoteVideo();
    setVideoStatus(`Un correspondant rejoint la salle, connexion en cours... Camera : ${activeCameraLabel}.`);
    await pc.setLocalDescription(await pc.createOffer());
    sendSignal({ type: "offer", sdp: pc.localDescription });
    return;
  }
  if (message.type === "leave") {
    createPeerConnection();
    resetRemoteVideo();
    setVideoStatus(`Le correspondant a quitte la salle. En attente... Camera : ${activeCameraLabel}.`);
    return;
  }
  if (message.type === "camera-state") {
    if (message.enabled === false) setVideoStatus(`Le correspondant a coupe sa camera. Votre camera : ${activeCameraLabel}.`);
    else if (remoteConnected) checkRemoteImage(peerConnection);
    return;
  }
  const pc = peerConnection;
  if (message.type === "offer") {
    // Both peers joining at the same instant both offer: the polite one yields.
    const polite = clientId < String(message.from || "");
    if (pc.signalingState !== "stable") {
      if (!polite) return;
      await pc.setLocalDescription({ type: "rollback" });
    }
    await pc.setRemoteDescription(message.sdp);
    await flushPendingCandidates(pc);
    await pc.setLocalDescription(await pc.createAnswer());
    sendSignal({ type: "answer", sdp: pc.localDescription });
    return;
  }
  if (message.type === "answer") {
    if (pc.signalingState !== "have-local-offer") return;
    await pc.setRemoteDescription(message.sdp);
    await flushPendingCandidates(pc);
    return;
  }
  if (message.type === "candidate") {
    if (!pc.remoteDescription) { pendingCandidates.push(message.candidate); return; }
    await pc.addIceCandidate(message.candidate).catch(() => {});
  }
}

function resetMediaButtons() {
  [["#toggle-mic", "Micro actif"], ["#toggle-camera", "Camera active"]].forEach(([selector, text]) => {
    const button = $(selector);
    const label = button.querySelector("span");
    if (label) label.textContent = text;
    button.setAttribute("aria-pressed", "false");
    button.classList.remove("is-muted");
  });
}

function endCall({ notifyServer = true } = {}) {
  sendSignal({ type: "leave" });
  peerConnection?.close(); peerConnection = null;
  const socket = signalSocket;
  signalSocket = null;
  socket?.close();
  localStream?.getTracks().forEach((track) => track.stop()); localStream = null;
  remoteConnected = false;
  pendingCandidates = [];
  activeCameraLabel = "";
  $("#local-video").srcObject = null;
  resetRemoteVideo();
  resetMediaButtons();
  if (isDoctor() && activeConsultation && notifyServer) {
    // Only the doctor closes the consultation; a patient who hangs up can rejoin while it is open.
    api(`/api/consultations/${encodeURIComponent(activeConsultation.room)}/end`, { method: "POST" }).catch(() => {});
    activeConsultation = null;
    setVideoStatus("Consultation terminee. Camera inactive.");
  } else if (!isDoctor() && activeConsultation) {
    setVideoStatus("Vous avez quitte la consultation. Vous pouvez la rejoindre tant que le medecin ne l'a pas terminee.");
  } else {
    setVideoStatus("Camera inactive.");
  }
  updateConsultationUi();
}

function toggleTrack(kind, button, activeText, mutedText) {
  const track = localStream?.getTracks().find((item) => item.kind === kind);
  if (!track) { toast("Activez d'abord la camera.", true); return; }
  track.enabled = !track.enabled;
  const label = button.querySelector("span");
  if (label) label.textContent = track.enabled ? activeText : mutedText;
  else button.textContent = track.enabled ? activeText : mutedText;
  button.setAttribute("aria-pressed", String(!track.enabled));
  button.classList.toggle("is-muted", !track.enabled);
  if (kind === "video") sendSignal({ type: "camera-state", enabled: track.enabled });
}

function wireInteractions() {
  $("#login-form").addEventListener("submit", submitLogin);
  document.querySelectorAll("[data-demo-user]").forEach((button) => button.addEventListener("click", () => {
    $("#login-username").value = button.dataset.demoUser;
    $("#login-password").value = "Demo-2026!";
    $("#login-error").textContent = "";
    $("#login-submit").focus();
  }));
  $("#logout-button").addEventListener("click", logout);
  document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => showView(button.dataset.view)));
  $("#open-video-doctor").addEventListener("click", () => { showView("video"); activateVideo(); });
  $("#open-video-patient").addEventListener("click", joinFromPatientSide);
  $("#invite-join").addEventListener("click", joinFromPatientSide);
  $("#alert-focus").addEventListener("click", () => { showView("doctor"); $("#alerts-panel").scrollIntoView({ behavior: "smooth", block: "center" }); });
  $("#vital-form").addEventListener("submit", submitVital);
  $("#consent-form").addEventListener("submit", submitConsent);
  $("#simulate-critical").addEventListener("click", () => { const form = $("#vital-form"); form.querySelector('[name="systolic"]').value = 188; form.querySelector('[name="diastolic"]').value = 122; form.querySelector('[name="heart_rate"]').value = 138; form.querySelector('[name="spo2"]').value = 89; form.querySelector('[name="temperature"]').value = 39.2; toast("Valeurs de cas degrade pre-remplies. Envoyez-les pour tester l'alerte."); });
  $("#alerts-list").addEventListener("click", (event) => { const target = event.target.closest(".acknowledge"); if (target) acknowledgeAlert(target.dataset.alertId); });
  $("#start-call").addEventListener("click", activateVideo);
  $("#camera-select").addEventListener("change", (event) => switchCamera(event.target.value));
  navigator.mediaDevices?.addEventListener?.("devicechange", refreshCameraList);
  $("#end-call").addEventListener("click", () => endCall());
  $("#toggle-mic").addEventListener("click", (event) => toggleTrack("audio", event.currentTarget, "Micro actif", "Micro coupe"));
  $("#toggle-camera").addEventListener("click", (event) => toggleTrack("video", event.currentTarget, "Camera active", "Camera coupee"));
  $(".mobile-menu").addEventListener("click", () => $(".sidebar").classList.toggle("open"));
}

document.addEventListener("DOMContentLoaded", () => {
  $("#today-label").textContent = new Intl.DateTimeFormat("fr-MA", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date());
  wireInteractions();
  restoreSession();
});

