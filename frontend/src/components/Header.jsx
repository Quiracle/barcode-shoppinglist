import React from "react";

function statusLabel(status) {
  if (status === "connected") return "Connected";
  if (status === "reconnecting") return "Reconnecting";
  if (status === "error") return "Connection error";
  return "Connecting";
}

export function Header({ listName, connectionStatus }) {
  return (
    <header className="header">
      <div>
        <h1>{listName || "My Shopping List"}</h1>
        <p>Always-on scanner mode</p>
      </div>
      <div className={`connection connection--${connectionStatus}`}>{statusLabel(connectionStatus)}</div>
    </header>
  );
}
