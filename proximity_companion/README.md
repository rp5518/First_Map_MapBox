# Proximity Companion (Foreground Web)

This is a separate companion web page that auto-marks an address as visited when all rules pass:

1. The nearest marker is within the threshold distance.
2. It is clearly nearer than the second nearest marker (margin rule).
3. The marker's state is reset/empty in Firestore.

It does not modify flag or notes history.

## What It Writes

The app writes only these fields to Firestore for a marker that is still reset:

- state: visited
- updatedBy: proximity
- proximityTimestamp: server timestamp

It uses merge writes and leaves other fields untouched.

## Important Behavior

- If state is already friendly, notfriendly, or visited, it does not overwrite.
- The companion is foreground web only.
- Beep alerts are intended for active screen usage.

## Run

1. Serve the First_Map_MapBox folder over HTTP (not file protocol).
2. Open proximity_companion/index.html in your phone browser.
3. Tap Load Marker List.
4. Tap Start Tracking and allow location.

## Optional Selected-Address Filter

Enable Use selected-address filter and paste one address per line. Only those addresses become eligible for auto-marking.
