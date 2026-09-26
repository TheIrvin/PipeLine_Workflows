# Recuperación

1. Comprueba docker compose ps y ./scripts/health-check.sh.
2. Revisa data/logs/pipeline.jsonl y los estados en data/ideas/ideas.db.
3. Corrige la causa y reinicia: docker compose restart production-worker.
4. El worker retoma desde el último checkpoint y conserva assets válidos.
5. Reanuda un job con POST http://localhost:8091/api/jobs/CONTENT-ID/resume.
6. La publicación solo se simula con publish-dry-run.

Crea un backup antes de cambiar Docker o el host con ./scripts/backup-n8n.sh.
