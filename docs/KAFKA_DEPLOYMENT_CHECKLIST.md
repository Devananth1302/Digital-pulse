# Kafka Integration - Deployment Checklist

## Pre-Deployment Verification

- [ ] All dependencies installed: `pip install -r requirements-kafka.txt`
- [ ] Kafka configuration reviewed: `config/kafka_config.yaml`
- [ ] Environment variables set if not using defaults
- [ ] Docker Compose file exists: `docker-compose.kafka.yml`
- [ ] Scripts are executable: `chmod +x scripts/kafka_*.py`

## Local Testing (30 minutes)

- [ ] Start Kafka: `docker-compose -f docker-compose.kafka.yml up -d`
- [ ] Verify Kafka health: `docker-compose -f docker-compose.kafka.yml ps`
- [ ] Test producer standalone: `python scripts/kafka_producer.py --test --stats`
- [ ] Test consumer standalone: `python scripts/kafka_consumer.py --batch 10 --stats`
- [ ] Test fallback queue:
  - [ ] Stop Kafka: `docker stop <kafka-container>`
  - [ ] Send message: `python scripts/kafka_producer.py --interactive`
  - [ ] Verify queue: `ls -la ./data/kafka_fallback_queue/`
  - [ ] Restart Kafka: `docker start <kafka-container>`
  - [ ] Retry queue: `python scripts/kafka_consumer.py --retry-fallback`

## Code Quality

- [ ] All imports verified: `python -m py_compile backend/streaming/*.py`
- [ ] No hardcoded credentials or endpoints
- [ ] Logging configured for debugging
- [ ] Error handling comprehensive
- [ ] Metrics collection implemented
- [ ] Test suite runs: `pytest tests/test_kafka_examples.py -v`

## Configuration

- [ ] `KAFKA_BOOTSTRAP_SERVERS` configured for target environment
- [ ] Security protocol set appropriately (PLAINTEXT, SASL_SSL, etc.)
- [ ] Topic names match expectations (raw_data, processed_results, dlq)
- [ ] Circuit breaker thresholds reviewed
- [ ] Fallback queue directory writable
- [ ] Queue size limits appropriate for disk space
- [ ] Retention policies set for topics

## Integration into FastAPI

- [ ] Producer integrated into `/upload-csv` endpoint (if needed)
- [ ] Consumer startup integrated into `@app.on_event("startup")`
- [ ] Health check endpoint added: `/health/kafka`
- [ ] Authentication/authorization reviewed if needed
- [ ] Error responses documented

## Monitoring Setup

- [ ] Metrics collection enabled in config
- [ ] Circuit breaker monitoring configured
- [ ] Fallback queue monitoring dashboard considered
- [ ] Log aggregation configured (if applicable)
- [ ] Alerting rules prepared for:
  - [ ] Circuit breaker OPEN state
  - [ ] Fallback queue growing too large
  - [ ] Consumer lag increasing
  - [ ] Producer failures
  - [ ] Kafka broker connection issues

## Documentation

- [ ] Team members read: `docs/KAFKA_INTEGRATION.md`
- [ ] Operations team reviewed: `docs/KAFKA_IMPLEMENTATION_GUIDE.md`
- [ ] Runbooks created for common issues
- [ ] API documentation exported/shared
- [ ] Configuration documented in deployment guide

## Security Review

- [ ] No credentials in code or config files
- [ ] Environment variables used for secrets
- [ ] SASL/SSL configured if connecting to secured Kafka
- [ ] TLS certificates in place (if using SSL)
- [ ] Network access restricted appropriately
- [ ] DLQ access controlled
- [ ] Fallback queue directory permissions restricted

## Performance Testing

- [ ] Tested with expected message volume
- [ ] Batch sizes optimized for throughput
- [ ] Consumer lag monitoring tested
- [ ] Fallback queue retry performance acceptable
- [ ] Memory usage within limits
- [ ] CPU usage reasonable
- [ ] Disk I/O acceptable

## Failover & Recovery Testing

- [ ] Circuit breaker recovery tested
- [ ] Fallback queue replay tested
- [ ] Graceful degradation when Kafka down verified
- [ ] Recovery after extended outage tested
- [ ] Offset management verified
- [ ] Exactly-once semantics confirmed

## Deployment Plan

- [ ] Phased rollout strategy documented
  - [ ] Phase 1: Production Kafka cluster setup
  - [ ] Phase 2: Producer integration in low-traffic endpoint
  - [ ] Phase 3: Consumer background processing
  - [ ] Phase 4: Full migration
- [ ] Rollback plan documented
- [ ] Canary testing planned
- [ ] Blue-green deployment considered

## Post-Deployment

- [ ] Health checks passing
- [ ] Metrics flowing to monitoring
- [ ] Logs appearing in aggregation system
- [ ] Alerts firing as expected (test alert rule)
- [ ] Performance within SLA
- [ ] No errors in application logs
- [ ] Circuit breaker state CLOSED
- [ ] Fallback queue empty
- [ ] Consumer lag stable and low

## Operational Readiness

- [ ] Runbooks written for:
  - [ ] Circuit breaker stuck OPEN
  - [ ] Fallback queue growing
  - [ ] Consumer lag high
  - [ ] Producer failures
  - [ ] Kafka broker connection issues
- [ ] Escalation path defined
- [ ] On-call rotation updated
- [ ] Knowledge transfer completed

## Compliance & Governance

- [ ] Data retention policies met
- [ ] Compliance requirements documented
- [ ] DLQ message retention verified
- [ ] Message encryption configured (if required)
- [ ] Audit logging enabled (if required)
- [ ] Data privacy checks passed

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| QA Lead | | | |
| DevOps | | | |
| Security | | | |
| Product | | | |

## Notes

```
[Space for deployment notes, issues encountered, resolutions, etc.]
```

---

## Rollback Procedure (if needed)

1. **Stop consumer:** `pkill -f kafka_consumer.py`
2. **Stop producer ingestion:** Disable in API
3. **Verify fallback queue:** Check `./data/kafka_fallback_queue/`
4. **Switch to batch processing:** Revert to existing batch job
5. **Preserve queue:** Keep fallback queue for later recovery
6. **Notify team:** Document any data loss or issues
7. **Post-mortem:** Schedule review meeting

---

## Contact & Support

**Technical Lead:** [Name/Contact]
**Operations:** [Contact]
**Documentation:** See `docs/KAFKA_INTEGRATION.md`
**Troubleshooting:** See `docs/KAFKA_IMPLEMENTATION_GUIDE.md`
