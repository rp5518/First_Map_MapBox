/*
Bulk marker reset helpers for the Mapbox canvassing map.
Module usage:
  import { resetAllMarkersWithPrompt } from './reset-markers.js';
  await resetAllMarkersWithPrompt(context);
*/
function getResetContext(ctx) {
    if (!ctx || !ctx.db || typeof ctx.createAddressId !== 'function') {
        throw new Error('Missing reset context. Expected { db, createAddressId }.');
    }
    return ctx;
}

async function loadAddressesFromMarkersJson(markersUrl) {
    const response = await fetch(markersUrl || 'markers.json');
    if (!response.ok) {
        throw new Error('Unable to load markers list from markers.json.');
    }

    const markers = await response.json();
    return markers
        .map((marker) => marker.address)
        .filter((address) => typeof address === 'string' && address.trim().length > 0);
}

function toUniqueAddresses(addresses) {
    const seen = new Set();
    const unique = [];

    addresses.forEach((address) => {
        const trimmed = address.trim();
        if (!seen.has(trimmed)) {
            seen.add(trimmed);
            unique.push(trimmed);
        }
    });

    return unique;
}

function buildUpdatePayload(options) {
    const payload = { state: '' };

    if (options.clearNotes) {
        payload.notesHistory = [];
    }

    if (options.clearFlags) {
        payload.flag = false;
    }

    return payload;
}

function chunk(values, size) {
    const chunkSize = Math.max(1, Number(size) || 300);
    const chunks = [];

    for (let i = 0; i < values.length; i += chunkSize) {
        chunks.push(values.slice(i, i + chunkSize));
    }

    return chunks;
}

export async function resetAllMarkers(context, userOptions) {
    const options = Object.assign(
        {
            clearNotes: true,
            clearFlags: false,
            dryRun: false,
            addresses: null,
            markersUrl: null,
            batchSize: 300
        },
        userOptions || {}
    );

    const ctx = getResetContext(context);

    let addresses = Array.isArray(options.addresses) ? options.addresses : null;
    if (!addresses || addresses.length === 0) {
        addresses = await loadAddressesFromMarkersJson(options.markersUrl || ctx.markersUrl);
    }

    addresses = toUniqueAddresses(addresses);
    const payload = buildUpdatePayload(options);

    const summary = {
        totalAddresses: addresses.length,
        clearNotes: options.clearNotes,
        clearFlags: options.clearFlags,
        dryRun: options.dryRun,
        updated: 0
    };

    if (options.dryRun) {
        console.log('Dry run summary:', summary);
        return summary;
    }

    const batches = chunk(addresses, options.batchSize);

    for (const batch of batches) {
        await Promise.all(
            batch.map((address) => {
                const addressId = ctx.createAddressId(address);
                return ctx.db.collection('markerStates').doc(addressId).set(payload, { merge: true });
            })
        );
        summary.updated += batch.length;
    }

    console.log('Reset complete:', summary);
    return summary;
}

export async function resetAllMarkersWithPrompt(context) {
    const modeInput = window.prompt(
        'Choose reset mode:\n' +
        '1) Reset all markers (preserve notes and flags) [recommended]\n' +
        '2) Reset all markers + clear notes (preserve flags)\n' +
        '3) Full reset (clear notes and flags)\n\n' +
        'Enter 1, 2, or 3:',
        '1'
    );

    if (modeInput === null) {
        return { cancelled: true };
    }

    const normalizedMode = String(modeInput).trim();
    if (!['1', '2', '3'].includes(normalizedMode)) {
        window.alert('Invalid selection. Please choose 1, 2, or 3.');
        return { cancelled: true, invalidSelection: true };
    }

    const clearNotes = normalizedMode === '2' || normalizedMode === '3';
    const clearFlags = normalizedMode === '3';

    const proceed = window.confirm(
        'Reset all markers now?\n\n' +
        'State: reset to default\n' +
        'Notes: ' + (clearNotes ? 'clear' : 'preserve') + '\n' +
        'Flags: ' + (clearFlags ? 'reset' : 'preserve')
    );

    if (!proceed) {
        return { cancelled: true };
    }

    const result = await resetAllMarkers(context, {
        clearNotes,
        clearFlags
    });

    window.alert('Reset complete. Updated ' + result.updated + ' marker records.');
    return result;
}
