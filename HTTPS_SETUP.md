# HTTPS Setup

This folder is configured for Firebase Hosting so the map and proximity companion can be served over HTTPS.

## What This Hosts

- `index.html`
- `markers.json`
- `reset-markers.js`
- `proximity_companion/index.html`
- `proximity_companion/app.js`
- `proximity_companion/styles.css`

## One-Time Login

From `C:\Users\wjg\Python_Stuff\First_Map_MapBox` run:

```powershell
npx.cmd firebase-tools login
```

## Quick HTTPS Preview URL

This creates a temporary HTTPS URL for testing on a phone:

```powershell
npm.cmd run hosting:preview
```

Firebase will print a public HTTPS URL. Open that URL on the phone.

## Production Deploy

This publishes Hosting for the `maps4canvasing` Firebase project:

```powershell
npm.cmd run hosting:deploy
```

## URLs After Deploy

Your pages will be available at paths like:

- `/index.html`
- `/proximity_companion/index.html`

## Notes

- HTTPS solves the phone geolocation restriction that blocked the LAN `http` test.
- `markers.json` is configured with `Cache-Control: no-cache` so marker updates are picked up more reliably.
- `local-config.js` remains excluded from deployment.