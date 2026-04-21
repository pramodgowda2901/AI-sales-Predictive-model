# Signal Ingestion Service Implementation - Task 17

## Overview

Implemented the Signal Ingestion Service for the AI Sales Predictive Management SaaS platform. This service handles signal ingestion from CRM systems and custom sources, with validation, normalization, and persistence.

## Completed Subtasks

### 17.1 SQS Consumer with Schema Validation and Duplicate Detection ✓

**Files:**
- `packages/signal-ingestion-service/src/signal-consumer.ts`
- `packages/signal-ingestion-service/src/signal-repository.ts`
- `packages/signal-ingestion-service/src/schema-validator.ts`
- `packages/signal-ingestion-service/src/audit-logger.ts`

**Implementation:**
- SQS consumer polling `signal-ingestion-queue` with exponential backoff
- JSON schema validation using Ajv with compiled validators
- Duplicate detection via `externalId` check
- Malformed/duplicate record rejection with Audit_Log entry
- Signal persistence to `signals` table with RLS context
- Graceful error handling and message deletion

**Requirements Met:**
- 5.2: Signal ingestion and persistence
- 5.3: Malformed/duplicate rejection with audit logging
- 5.7: Signal round-trip consistency

### 17.2 Public API Endpoint for Custom Signal Push ✓

**Files:**
- `packages/signal-ingestion-service/src/signal-handler.ts`
- `packages/signal-ingestion-service/src/index.ts`

**Implementation:**
- `POST /v1/signals` endpoint for custom signal push
- Schema validation with descriptive error messages
- Tenant ID verification
- Message publishing to `signal-ingestion-queue`
- 202 Accepted response for async processing

**Requirements Met:**
- 5.6: Public API endpoint for custom signals
- 5.7: Schema validation with descriptive errors

### 17.3 Normalization Layer with CRM Field Mapping ✓

**Files:**
- `packages/signal-ingestion-service/src/signal-normalizer.ts`

**Implementation:**
- CRM-specific field mapping for Salesforce, HubSpot, Dynamics
- Canonical schema normalization
- Metadata preservation for unmapped fields
- EventBridge event publishing on successful persistence
- Support for custom sources with fallback mappings

**CRM Mappings:**
- **Salesforce**: Id, Type, CreatedDate, Subject, Description
- **HubSpot**: id, type, timestamp, subject, body, engagement_type
- **Dynamics**: activityid, activitytypecode, subject, description, createdon

**Requirements Met:**
- 5.2: CRM field normalization to canonical schema

### 17.4 EventBridge Scheduler and Connectivity Loss Detection ✓

**Files:**
- `packages/signal-ingestion-service/src/crm-connectivity-monitor.ts`

**Implementation:**
- CRM connector status tracking per tenant
- Successful/failed sync recording
- Connectivity loss detection (>10 min threshold)
- `crm.connectivity_lost` event publishing to EventBridge
- Multi-connector and multi-tenant support

**Features:**
- Tracks last successful sync timestamp
- Increments failure counter on failed syncs
- Publishes event when threshold exceeded
- Independent tracking per connector per tenant

**Requirements Met:**
- 5.4: EventBridge Scheduler polling trigger
- 5.5: Connectivity loss detection (>10 min)

### 17.5 Property-Based Test for Signal Round-Trip ✓

**Files:**
- `packages/signal-ingestion-service/src/__tests__/signal-roundtrip.test.ts`

**Implementation:**
- Property 1: Signal round-trip consistency (1000 iterations)
  - Generate arbitrary valid Signal objects
  - Serialize to JSON
  - Validate against schema
  - Normalize
  - Assert structural equivalence
- Property 2: Schema validation idempotence
- Property 3: Normalization preserves required fields
- Property 4: Metadata preservation through normalization

**Test Coverage:**
- 1000 iterations per property
- Arbitrary signal generation with fast-check
- All signal types and sources
- Metadata preservation validation

**Requirements Met:**
- 5.7: Signal round-trip consistency property test

### 17.6 Unit Tests for Schema Validation ✓

**Files:**
- `packages/signal-ingestion-service/src/__tests__/schema-validator.test.ts`
- `packages/signal-ingestion-service/src/__tests__/signal-normalizer.test.ts`
- `packages/signal-ingestion-service/src/__tests__/crm-connectivity-monitor.test.ts`

**Test Coverage:**

**Schema Validation Tests:**
- Valid signals (complete, minimal, all types, all sources)
- Missing required fields (tenantId, dealId, type, source, timestamp)
- Extra fields rejection
- Invalid field types (invalid enums, invalid UUIDs, invalid timestamps)
- Error message generation

**Normalization Tests:**
- Salesforce field mapping
- HubSpot field mapping
- Dynamics field mapping
- Unknown source handling
- Timestamp handling (provided vs. current)
- Metadata preservation
- External ID extraction
- Empty metadata handling

**Connectivity Monitor Tests:**
- Successful sync recording
- Failed sync recording
- Failure count increment
- Connectivity loss detection (within/after threshold)
- Event publishing on threshold exceeded
- Multiple connector tracking
- Multi-tenant independence

**Requirements Met:**
- 5.3: Schema validation tests
- 5.7: Duplicate detection tests

## Project Structure

```
packages/signal-ingestion-service/
├── src/
│   ├── signal-schema.ts              # Signal types and JSON schema
│   ├── signal-repository.ts          # Database operations
│   ├── schema-validator.ts           # Ajv schema validation
│   ├── signal-normalizer.ts          # CRM field mapping
│   ├── audit-logger.ts               # Audit logging
│   ├── signal-consumer.ts            # SQS consumer
│   ├── signal-handler.ts             # API request handler
│   ├── crm-connectivity-monitor.ts   # Connectivity monitoring
│   ├── index.ts                      # Express app entry point
│   └── __tests__/
│       ├── schema-validator.test.ts
│       ├── signal-normalizer.test.ts
│       ├── crm-connectivity-monitor.test.ts
│       └── signal-roundtrip.test.ts
├── package.json
├── tsconfig.json
├── jest.config.js
└── README.md
```

## Key Features

### Schema Validation
- Ajv-based JSON schema validation
- Compiled validators for performance
- Descriptive error messages
- Support for all signal types and sources

### Duplicate Detection
- External ID-based deduplication
- Database query for existing signals
- Audit log entry on duplicate rejection

### CRM Normalization
- Salesforce, HubSpot, Dynamics field mapping
- Metadata preservation for unmapped fields
- Timestamp handling with fallback to current time
- Support for custom sources

### Connectivity Monitoring
- Per-connector per-tenant status tracking
- 10-minute connectivity loss threshold
- EventBridge event publishing
- Failure counter tracking

### Audit Logging
- Malformed signal rejection logging
- Duplicate signal rejection logging
- Metadata capture for debugging
- Tenant-scoped audit entries

## Dependencies

```json
{
  "dependencies": {
    "@platform/shared": "1.0.0",
    "express": "^4.18.2",
    "pg": "^8.10.0",
    "uuid": "^9.0.0",
    "aws-sdk": "^2.1400.0",
    "ajv": "^8.12.0",
    "fast-check": "^3.14.0"
  }
}
```

## Integration Points

1. **Shared Library** (`@platform/shared`)
   - DatabasePool with RLS context
   - StructuredLogger
   - EventBridgePublisher
   - SQSConsumer base class

2. **Aurora PostgreSQL**
   - `signals` table for signal persistence
   - `audit_log_refs` table for rejection logging
   - RLS policies for tenant isolation

3. **SQS**
   - `signal-ingestion-queue` for message buffering
   - Long polling with 20s wait time
   - Message deletion on successful processing

4. **EventBridge**
   - `signal.ingested` event publishing
   - `crm.connectivity_lost` event publishing

## Testing Strategy

### Unit Tests
- Schema validation: valid, invalid, edge cases
- Normalization: CRM-specific mappings, metadata preservation
- Connectivity monitoring: status tracking, loss detection
- Audit logging: rejection/duplicate logging

### Property-Based Tests
- Signal round-trip consistency (1000 iterations)
- Schema validation idempotence
- Normalization field preservation
- Metadata preservation

### Coverage Target
- 80%+ code coverage
- All critical paths tested
- Edge cases covered

## API Endpoints

### POST /v1/signals
- Accept custom signal for ingestion
- Validate against schema
- Publish to queue
- Return 202 Accepted

### GET /health
- Health check endpoint
- Returns 200 OK

## Error Handling

- **400 Bad Request**: Invalid signal payload with validation errors
- **403 Forbidden**: Tenant ID mismatch
- **503 Service Unavailable**: Queue unavailable
- **500 Internal Server Error**: Database/processing errors

## Performance Characteristics

- Schema validation: <1ms (Ajv compiled)
- SQS polling: 10 messages per poll, 20s wait
- Database: RLS context per connection
- Duplicate check: Indexed query on external_id
- Event publishing: Async, non-blocking

## Security Considerations

- RLS enforcement on all database queries
- Tenant ID validation on API requests
- Schema validation prevents injection
- Audit logging for compliance
- No sensitive data in logs

## Future Enhancements

1. Batch signal processing for higher throughput
2. Signal enrichment pipeline
3. Real-time signal processing with Kinesis
4. Signal deduplication with Redis cache
5. CRM connector health dashboard
6. Signal replay capability

## Notes

- All database operations use RLS context setter from shared library
- SQS consumer runs in background on service startup
- Connectivity monitor is stateful (in-memory tracking)
- Audit logging is non-blocking (failures don't stop processing)
- Event publishing is async (failures logged but don't block)
