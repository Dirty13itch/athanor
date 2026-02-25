#!/usr/bin/env bash
# Backup Neo4j graph via Cypher export.
# Runs on VAULT (where Neo4j is deployed).
# Exports all nodes and relationships as Cypher CREATE statements.
#
# Usage: ./backup-neo4j.sh
# Cron:  0 3 * * * /opt/athanor/scripts/backup-neo4j.sh >> /var/log/athanor-backup.log 2>&1

set -euo pipefail

NEO4J_URL="http://localhost:7474"
NEO4J_USER="neo4j"
NEO4J_PASS="athanor2026"
BACKUP_DIR="/mnt/user/backups/athanor/neo4j"
RETENTION_DAYS=7
DATE=$(date +%Y-%m-%d)

echo "[$(date -Iseconds)] Starting Neo4j backup"

mkdir -p "$BACKUP_DIR"

DEST="$BACKUP_DIR/graph_${DATE}.cypher"

# Export all nodes with labels and properties
python3 -c "
import json, sys, urllib.request, base64

url = '${NEO4J_URL}/db/neo4j/tx/commit'
auth = base64.b64encode(b'${NEO4J_USER}:${NEO4J_PASS}').decode()
headers = {'Content-Type': 'application/json', 'Authorization': f'Basic {auth}'}

def run_cypher(statement):
    data = json.dumps({'statements': [{'statement': statement}]}).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

# Export nodes
result = run_cypher('MATCH (n) RETURN labels(n) AS labels, properties(n) AS props')
rows = result.get('results', [{}])[0].get('data', [])

lines = ['// Neo4j backup generated $(date -Iseconds)', '// Nodes']
for row in rows:
    labels, props = row['row']
    label_str = ':'.join(labels)
    props_str = json.dumps(props)
    lines.append(f'CREATE (:{label_str} {props_str});')

# Export relationships
result = run_cypher('''
    MATCH (a)-[r]->(b)
    RETURN labels(a)[0] AS a_label, a.name AS a_name,
           type(r) AS rel_type, properties(r) AS rel_props,
           labels(b)[0] AS b_label, b.name AS b_name
''')
rows = result.get('results', [{}])[0].get('data', [])

lines.append('')
lines.append('// Relationships')
for row in rows:
    a_label, a_name, rel_type, rel_props, b_label, b_name = row['row']
    props_str = json.dumps(rel_props) if rel_props else ''
    props_clause = f' {props_str}' if props_str and props_str != '{}' else ''
    lines.append(f'MATCH (a:{a_label} {{name: {json.dumps(a_name)}}}), (b:{b_label} {{name: {json.dumps(b_name)}}}) CREATE (a)-[:{rel_type}{props_clause}]->(b);')

print('\n'.join(lines))
" > "$DEST"

if [ -f "$DEST" ] && [ -s "$DEST" ]; then
    LINES=$(wc -l < "$DEST")
    SIZE=$(du -h "$DEST" | cut -f1)
    echo "[$(date -Iseconds)] Saved Neo4j export: $DEST ($LINES lines, $SIZE)"
else
    echo "[$(date -Iseconds)] ERROR: Neo4j export failed or empty"
    exit 1
fi

# Prune old backups
echo "[$(date -Iseconds)] Pruning backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -name "graph_*.cypher" -mtime +$RETENTION_DAYS -delete -print

echo "[$(date -Iseconds)] Neo4j backup complete"
