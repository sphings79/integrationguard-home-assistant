import type {
  Channel,
  HistoryEvent,
  HomeAssistant,
  PanelData,
  Rule,
  Settings,
  Severity,
} from "./types";

/** Thin wrapper around the panel's WebSocket commands. */
export class IntegrationGuardApi {
  constructor(private hass: HomeAssistant) {}

  /** Point the wrapper at a fresher hass object. */
  update(hass: HomeAssistant): void {
    this.hass = hass;
  }

  get(): Promise<PanelData> {
    return this.hass.callWS({ type: "integrationguard/get" });
  }

  scan(force = false): Promise<{ ok: boolean }> {
    return this.hass.callWS({ type: "integrationguard/scan", force });
  }

  saveSettings(
    settings: Settings,
    githubToken?: string,
  ): Promise<{ ok: boolean }> {
    const message: Record<string, unknown> = {
      type: "integrationguard/settings/save",
      settings,
    };
    // Only sent when the field was actually touched, so an untouched form
    // never clears a stored token.
    if (githubToken !== undefined) message.github_token = githubToken;
    return this.hass.callWS(message);
  }

  saveRules(rules: Rule[]): Promise<{ ok: boolean }> {
    return this.hass.callWS({ type: "integrationguard/rules/save", rules });
  }

  saveSeverities(severities: Severity[]): Promise<{ ok: boolean }> {
    return this.hass.callWS({
      type: "integrationguard/severities/save",
      severities,
    });
  }

  saveChannel(channel: Channel): Promise<{ channel: Channel }> {
    return this.hass.callWS({
      type: "integrationguard/channels/save",
      channel,
    });
  }

  deleteChannel(id: string): Promise<{ ok: boolean }> {
    // Not "id": that key belongs to the WebSocket protocol itself.
    return this.hass.callWS({
      type: "integrationguard/channels/delete",
      channel_id: id,
    });
  }

  testChannel(channel: Channel): Promise<{ ok: boolean }> {
    return this.hass.callWS({ type: "integrationguard/channels/test", channel });
  }

  ignore(
    key: string,
    ignored: boolean,
    until: string | null = null,
    reason = "",
  ): Promise<{ ok: boolean }> {
    return this.hass.callWS({
      type: "integrationguard/ignore",
      key,
      ignored,
      until,
      reason,
    });
  }

  markUsed(key: string, used: boolean): Promise<{ ok: boolean }> {
    return this.hass.callWS({ type: "integrationguard/mark_used", key, used });
  }

  history(filters: {
    limit?: number;
    key?: string | null;
    kind?: string | null;
  }): Promise<{ events: HistoryEvent[] }> {
    return this.hass.callWS({ type: "integrationguard/history", ...filters });
  }
}
