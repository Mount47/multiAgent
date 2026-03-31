// WebSocket message types from backend

export interface WsEventMessage {
  type: 'event'
  timestamp: string
  source: string
  content: string
}

export interface WsStateChangeMessage {
  type: 'state_change'
  agent: string
  state: string
}

export interface WsStatusMessage {
  type: 'status'
  status: string
  error?: string
}

// HITL: Approval request from backend
export interface WsApprovalRequestMessage {
  type: 'approval_request'
  checkpoint: string
  content: {
    agent: string
    content: string
    checkpoint: string
  }
}

export type WsMessage = WsEventMessage | WsStateChangeMessage | WsStatusMessage | WsApprovalRequestMessage
