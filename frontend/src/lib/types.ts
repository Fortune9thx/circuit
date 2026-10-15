/** The contract's JSON records, as the views return them. */

export type Decision =
  | "TRIGGER_CONFIRMED"
  | "NOT_CONFIRMED"
  | "INSUFFICIENT"
  | "CONFLICTING"
  | "STALE"
  | "TAMPERED";

export type IncidentStatus = "OPEN" | "ASSESSED" | "EXPIRED";

export interface Charter {
  charter_id: string;
  author: string;
  policy: string;
  evidence_patterns: string[];
  target: string;
  action_class: string;
  max_duration_minutes: number;
  /** Wei, as a decimal string — exact beyond 2**53. */
  bond_amount: string;
  fee_amount: string;
  treasury: string;
  charter_hash: string;
  created_at: number;
}

export interface Incident {
  incident_id: string;
  incident_key: string;
  charter_id: string;
  charter_hash: string;
  target: string;
  action_class: string;
  scope: string;
  duration_minutes: number;
  evidence_urls: string[];
  digest: string;
  assessor: string;
  /** Wei, as a decimal string — exact beyond 2**53. */
  bond: string;
  fee: string;
  status: IncidentStatus;
  decision: Decision | "";
  code: string;
  supporting_sources: number[];
  clause_ids: string[];
  findings_hash: string;
  capability_id: string;
  created_at: number;
  assessed_at: number;
}

export interface Capability {
  capability_id: string;
  incident_id: string;
  charter_id: string;
  digest: string;
  target: string;
  action_class: string;
  scope: string;
  duration_minutes: number;
  issued_at: number;
  expires_at: number;
  consumed: boolean;
  consumed_by: string;
  consumed_at: number;
  expired: boolean;
}

export interface BoardEntry {
  incident_id: string;
  charter_id: string;
  status: IncidentStatus;
  decision: Decision | "";
  target: string;
  action_class: string;
  created_at: number;
}

export interface Config {
  owner: string;
  treasury: string;
  min_duration_minutes: number;
  max_duration_minutes: number;
  assess_delay_seconds: number;
  stuck_timeout_seconds: number;
  max_evidence_urls: number;
  next_charter: number;
  next_incident: number;
  next_capability: number;
}
