(function () {
    "use strict";

    const firebaseConfig = {
        apiKey: "AIzaSyCm-dDUMYN4JLdIyt0FT0BzBIRLCHXm8EU",
        authDomain: "maps4canvasing.firebaseapp.com",
        projectId: "maps4canvasing",
        storageBucket: "maps4canvasing.firebasestorage.app",
        messagingSenderId: "913974581293",
        appId: "1:913974581293:web:201a7403bc5d9c82d900a4",
        measurementId: "G-X0G2YNP37H"
    };

    firebase.initializeApp(firebaseConfig);
    const db = firebase.firestore();

    const MODE_PRESETS = {
        test: {
            thresholdFeet: 80,
            nearestMarginFeet: 0,
            minMoveFeet: 0,
            maxAccuracyFeet: 200,
            cooldownSeconds: 0,
            pollMs: 1200,
            hint: "Easy-trigger settings for proving end-to-end behavior."
        },
        field: {
            thresholdFeet: 50,
            nearestMarginFeet: 8,
            minMoveFeet: 10,
            maxAccuracyFeet: 100,
            cooldownSeconds: 60,
            pollMs: 1500,
            hint: "Balanced settings for normal walking routes."
        },
        strict: {
            thresholdFeet: 35,
            nearestMarginFeet: 12,
            minMoveFeet: 15,
            maxAccuracyFeet: 70,
            cooldownSeconds: 120,
            pollMs: 1800,
            hint: "Stricter settings to reduce false positives in dense areas."
        }
    };

    const els = {
        modeSelect: document.getElementById("mode-select"),
        applyModeBtn: document.getElementById("apply-mode-btn"),
        modeHint: document.getElementById("mode-hint"),
        thresholdFeet: document.getElementById("threshold-feet"),
        nearestMarginFeet: document.getElementById("nearest-margin-feet"),
        minMoveFeet: document.getElementById("min-move-feet"),
        maxAccuracyFeet: document.getElementById("max-accuracy-feet"),
        cooldownSeconds: document.getElementById("cooldown-seconds"),
        pollMs: document.getElementById("poll-ms"),
        selectedOnly: document.getElementById("selected-only"),
        selectedAddresses: document.getElementById("selected-addresses"),
        beepEnabled: document.getElementById("beep-enabled"),
        loadMarkersBtn: document.getElementById("load-markers-btn"),
        startBtn: document.getElementById("start-btn"),
        stopBtn: document.getElementById("stop-btn"),
        markersLoaded: document.getElementById("markers-loaded"),
        eligibleMarkers: document.getElementById("eligible-markers"),
        trackingState: document.getElementById("tracking-state"),
        lastPosition: document.getElementById("last-position"),
        lastAction: document.getElementById("last-action"),
        log: document.getElementById("log")
    };

    let allMarkers = [];
    let watchId = null;
    let lastPosition = null;
    let audioContext = null;
    const markerCooldownMsById = new Map();

    function logLine(message) {
        const now = new Date().toLocaleTimeString();
        const line = "[" + now + "] " + message;
        els.log.textContent = line + "\n" + els.log.textContent;
    }

    function createAddressId(address) {
        return String(address || "")
            .replace(/[^a-zA-Z0-9]/g, "_")
            .toLowerCase();
    }

    function areCurrentSettingsEqualToPreset(preset) {
        return (
            Number(els.thresholdFeet.value) === preset.thresholdFeet &&
            Number(els.nearestMarginFeet.value) === preset.nearestMarginFeet &&
            Number(els.minMoveFeet.value) === preset.minMoveFeet &&
            Number(els.maxAccuracyFeet.value) === preset.maxAccuracyFeet &&
            Number(els.cooldownSeconds.value) === preset.cooldownSeconds &&
            Number(els.pollMs.value) === preset.pollMs
        );
    }

    function syncModeFromCurrentSettings() {
        if (areCurrentSettingsEqualToPreset(MODE_PRESETS.test)) {
            els.modeSelect.value = "test";
            els.modeHint.textContent = MODE_PRESETS.test.hint;
            return;
        }
        if (areCurrentSettingsEqualToPreset(MODE_PRESETS.field)) {
            els.modeSelect.value = "field";
            els.modeHint.textContent = MODE_PRESETS.field.hint;
            return;
        }
        if (areCurrentSettingsEqualToPreset(MODE_PRESETS.strict)) {
            els.modeSelect.value = "strict";
            els.modeHint.textContent = MODE_PRESETS.strict.hint;
            return;
        }

        els.modeSelect.value = "custom";
        els.modeHint.textContent = "Manual values are active.";
    }

    function applyModePreset(mode) {
        const preset = MODE_PRESETS[mode];
        if (!preset) {
            return;
        }

        els.thresholdFeet.value = String(preset.thresholdFeet);
        els.nearestMarginFeet.value = String(preset.nearestMarginFeet);
        els.minMoveFeet.value = String(preset.minMoveFeet);
        els.maxAccuracyFeet.value = String(preset.maxAccuracyFeet);
        els.cooldownSeconds.value = String(preset.cooldownSeconds);
        els.pollMs.value = String(preset.pollMs);
        els.modeHint.textContent = preset.hint;

        logLine("Applied mode: " + mode);
    }

    function getSettings() {
        return {
            thresholdFeet: Number(els.thresholdFeet.value) || 30,
            nearestMarginFeet: Number(els.nearestMarginFeet.value) || 10,
            minMoveFeet: Number(els.minMoveFeet.value) || 12,
            maxAccuracyFeet: Number(els.maxAccuracyFeet.value) || 50,
            cooldownMs: (Number(els.cooldownSeconds.value) || 90) * 1000,
            pollMs: Number(els.pollMs.value) || 1500
        };
    }

    function parseSelectedAddresses() {
        const lines = String(els.selectedAddresses.value || "")
            .split(/\r?\n/)
            .map((line) => line.trim())
            .filter(Boolean);
        return new Set(lines.map(createAddressId));
    }

    function getEligibleMarkers() {
        if (!els.selectedOnly.checked) {
            return allMarkers;
        }

        const selected = parseSelectedAddresses();
        return allMarkers.filter((m) => selected.has(m.addressId));
    }

    function updateEligibleCounter() {
        els.eligibleMarkers.textContent = String(getEligibleMarkers().length);
    }

    function metersToFeet(meters) {
        return meters * 3.280839895;
    }

    function haversineFeet(lat1, lon1, lat2, lon2) {
        const toRad = Math.PI / 180;
        const dLat = (lat2 - lat1) * toRad;
        const dLon = (lon2 - lon1) * toRad;
        const a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * toRad) * Math.cos(lat2 * toRad) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        const earthMeters = 6371000;
        return metersToFeet(earthMeters * c);
    }

    function distanceBetweenPositionFeet(a, b) {
        return haversineFeet(a.lat, a.lng, b.lat, b.lng);
    }

    function findNearestTwo(position, candidates) {
        let nearest = null;
        let second = null;

        for (const marker of candidates) {
            const d = haversineFeet(position.lat, position.lng, marker.lat, marker.lng);
            if (!nearest || d < nearest.distanceFeet) {
                second = nearest;
                nearest = { marker, distanceFeet: d };
            } else if (!second || d < second.distanceFeet) {
                second = { marker, distanceFeet: d };
            }
        }

        return { nearest, second };
    }

    async function tryMarkVisited(marker) {
        const docRef = db.collection("markerStates").doc(marker.addressId);

        return db.runTransaction(async (tx) => {
            const snap = await tx.get(docRef);
            const data = snap.exists ? snap.data() : {};
            const state = String(data.state || "").trim();

            if (state !== "") {
                return {
                    changed: false,
                    reason: "already_has_state",
                    currentState: state
                };
            }

            tx.set(docRef, {
                state: "visited",
                updatedBy: "proximity",
                proximityTimestamp: firebase.firestore.FieldValue.serverTimestamp()
            }, { merge: true });

            return {
                changed: true,
                reason: "set_visited"
            };
        });
    }

    function ensureAudioContext() {
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        return audioContext;
    }

    async function playBeep() {
        if (!els.beepEnabled.checked) {
            return;
        }

        try {
            const ctx = ensureAudioContext();
            if (ctx.state === "suspended") {
                await ctx.resume();
            }

            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            osc.type = "sine";
            osc.frequency.value = 880;
            gain.gain.value = 0.001;

            osc.connect(gain);
            gain.connect(ctx.destination);

            const t = ctx.currentTime;
            gain.gain.exponentialRampToValueAtTime(0.13, t + 0.01);
            gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.18);

            osc.start(t);
            osc.stop(t + 0.2);
        } catch (error) {
            logLine("Audio warning: " + (error && error.message ? error.message : error));
        }
    }

    async function handlePosition(position) {
        const settings = getSettings();
        const fix = {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            accuracyFeet: metersToFeet(position.coords.accuracy)
        };

        els.lastPosition.textContent =
            fix.lat.toFixed(6) + ", " + fix.lng.toFixed(6) +
            " (accuracy +/ - " + Math.round(fix.accuracyFeet) + " ft)";

        if (fix.accuracyFeet > settings.maxAccuracyFeet) {
            els.lastAction.textContent = "Ignored: poor GPS accuracy";
            return;
        }

        if (lastPosition) {
            const moveFeet = distanceBetweenPositionFeet(lastPosition, fix);
            if (moveFeet < settings.minMoveFeet) {
                els.lastAction.textContent = "Ignored: movement below threshold";
                return;
            }
        }

        lastPosition = { lat: fix.lat, lng: fix.lng };

        const candidates = getEligibleMarkers();
        updateEligibleCounter();
        if (candidates.length === 0) {
            els.lastAction.textContent = "No eligible markers";
            return;
        }

        const nearestInfo = findNearestTwo(fix, candidates);
        if (!nearestInfo.nearest) {
            els.lastAction.textContent = "No nearest marker found";
            return;
        }

        const nearest = nearestInfo.nearest;
        const second = nearestInfo.second;

        if (nearest.distanceFeet > settings.thresholdFeet) {
            els.lastAction.textContent =
                "Nearest is outside threshold: " + Math.round(nearest.distanceFeet) + " ft";
            return;
        }

        if (second && nearest.distanceFeet + settings.nearestMarginFeet >= second.distanceFeet) {
            els.lastAction.textContent = "Ambiguous nearest marker, skipped";
            return;
        }

        const lastMarkedAt = markerCooldownMsById.get(nearest.marker.addressId) || 0;
        const now = Date.now();
        if (now - lastMarkedAt < settings.cooldownMs) {
            els.lastAction.textContent = "Cooldown active for nearest marker";
            return;
        }

        try {
            const result = await tryMarkVisited(nearest.marker);
            if (result.changed) {
                markerCooldownMsById.set(nearest.marker.addressId, now);
                els.lastAction.textContent =
                    "Auto-marked visited at " + Math.round(nearest.distanceFeet) + " ft";
                logLine(
                    "Marked visited: " + nearest.marker.address +
                    " | distance " + Math.round(nearest.distanceFeet) + " ft"
                );
                await playBeep();
            } else {
                els.lastAction.textContent =
                    "Skipped, already set: " + String(result.currentState || "unknown");
            }
        } catch (error) {
            const msg = error && error.message ? error.message : String(error);
            els.lastAction.textContent = "Transaction error";
            logLine("Firestore transaction error: " + msg);
        }
    }

    function onPositionError(error) {
        const msg = error && error.message ? error.message : "Unknown geolocation error";
        els.lastAction.textContent = "Location error";
        logLine("Geolocation error: " + msg);
    }

    async function loadMarkers() {
        const response = await fetch("../markers.json", { cache: "no-store" });
        if (!response.ok) {
            throw new Error("Unable to load ../markers.json (status " + response.status + ")");
        }

        const raw = await response.json();
        allMarkers = raw
            .filter((m) => Number.isFinite(Number(m.lat)) && Number.isFinite(Number(m.lng)) && m.address)
            .map((m) => ({
                address: m.address,
                addressId: createAddressId(m.address),
                lat: Number(m.lat),
                lng: Number(m.lng)
            }));

        els.markersLoaded.textContent = String(allMarkers.length);
        updateEligibleCounter();
        logLine("Loaded " + allMarkers.length + " markers from ../markers.json");
    }

    function startTracking() {
        if (watchId !== null) {
            return;
        }

        if (!navigator.geolocation) {
            throw new Error("This browser does not support geolocation");
        }

        if (allMarkers.length === 0) {
            throw new Error("Load markers before starting tracking");
        }

        const settings = getSettings();
        watchId = navigator.geolocation.watchPosition(
            (position) => {
                handlePosition(position);
            },
            onPositionError,
            {
                enableHighAccuracy: true,
                timeout: 12000,
                maximumAge: Math.max(0, settings.pollMs)
            }
        );

        els.trackingState.textContent = "Running";
        els.startBtn.disabled = true;
        els.stopBtn.disabled = false;
        logLine("Tracking started");

        // Prime audio permission while this user gesture is active.
        ensureAudioContext();
    }

    function stopTracking() {
        if (watchId !== null) {
            navigator.geolocation.clearWatch(watchId);
            watchId = null;
        }

        els.trackingState.textContent = "Stopped";
        els.startBtn.disabled = false;
        els.stopBtn.disabled = true;
        logLine("Tracking stopped");
    }

    els.loadMarkersBtn.addEventListener("click", async function () {
        try {
            await loadMarkers();
            els.lastAction.textContent = "Markers loaded";
        } catch (error) {
            const msg = error && error.message ? error.message : String(error);
            els.lastAction.textContent = "Load markers failed";
            logLine("Load error: " + msg);
        }
    });

    els.startBtn.addEventListener("click", function () {
        try {
            startTracking();
        } catch (error) {
            const msg = error && error.message ? error.message : String(error);
            els.lastAction.textContent = "Start failed";
            logLine("Start error: " + msg);
        }
    });

    els.stopBtn.addEventListener("click", function () {
        stopTracking();
    });

    els.selectedOnly.addEventListener("change", updateEligibleCounter);
    els.selectedAddresses.addEventListener("input", updateEligibleCounter);

    els.applyModeBtn.addEventListener("click", function () {
        const mode = els.modeSelect.value;
        if (mode === "custom") {
            els.modeHint.textContent = "Custom mode keeps your manual values unchanged.";
            logLine("Custom mode selected (no preset applied)");
            return;
        }

        applyModePreset(mode);
    });

    els.modeSelect.addEventListener("change", function () {
        if (els.modeSelect.value === "custom") {
            els.modeHint.textContent = "Custom mode keeps your manual values unchanged.";
            return;
        }

        const preset = MODE_PRESETS[els.modeSelect.value];
        if (preset) {
            els.modeHint.textContent = preset.hint;
        }
    });

    [
        els.thresholdFeet,
        els.nearestMarginFeet,
        els.minMoveFeet,
        els.maxAccuracyFeet,
        els.cooldownSeconds,
        els.pollMs
    ].forEach(function (inputEl) {
        inputEl.addEventListener("input", syncModeFromCurrentSettings);
    });

    applyModePreset("field");
    syncModeFromCurrentSettings();

    logLine("Ready. Load markers, then start tracking.");
})();
