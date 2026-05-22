//! HTTP and WebSocket handler boundaries.
//!
//! Suggested handler grouping:
//! - auth: login / refresh / jwt validation
//! - profile: user goals and structured user settings
//! - plans: daily plan CRUD and status transitions
//! - workshop_ws: long-lived socket for tutoring streams
//! - health: liveness/readiness probes
//!
//! This module currently defines architecture-only placeholders.
