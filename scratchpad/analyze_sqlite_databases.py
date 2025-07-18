#!/usr/bin/env python3
"""
SQLite Database Analysis Script for PostgreSQL Migration Planning
Part of Agent Hive Production Readiness - Database Migration Agent

Analyzes all SQLite databases in the project to understand schema,
data volume, and relationships for PostgreSQL migration planning.
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import sys

def analyze_database(db_path: str) -> Dict[str, Any]:
    """
    Analyze SQLite database schema and data.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        Dictionary containing schema and data analysis
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get database info
        cursor.execute("PRAGMA database_list")
        db_info = cursor.fetchall()
        
        # Get table schemas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        schema_info = {}
        total_rows = 0
        
        for table in tables:
            table_name = table[0]
            
            # Skip sqlite internal tables
            if table_name.startswith('sqlite_'):
                continue
                
            # SECURITY FIX: Use identifier quoting to prevent SQL injection
            # Get table info
            cursor.execute(f"PRAGMA table_info(`{table_name}`)")
            columns = cursor.fetchall()
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            row_count = cursor.fetchone()[0]
            total_rows += row_count
            
            # Get indexes
            cursor.execute(f"PRAGMA index_list(`{table_name}`)")
            indexes = cursor.fetchall()
            
            # Get foreign keys
            cursor.execute(f"PRAGMA foreign_key_list(`{table_name}`)")
            foreign_keys = cursor.fetchall()
            
            # Sample some data for type analysis
            sample_data = []
            if row_count > 0:
                cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 3")
                sample_data = cursor.fetchall()
            
            schema_info[table_name] = {
                "columns": [
                    {
                        "name": col[1],
                        "type": col[2],
                        "not_null": bool(col[3]),
                        "default_value": col[4],
                        "primary_key": bool(col[5])
                    }
                    for col in columns
                ],
                "row_count": row_count,
                "indexes": [
                    {
                        "name": idx[1],
                        "unique": bool(idx[2]),
                        "partial": bool(idx[4])
                    }
                    for idx in indexes
                ],
                "foreign_keys": [
                    {
                        "column": fk[3],
                        "references_table": fk[2],
                        "references_column": fk[4]
                    }
                    for fk in foreign_keys
                ],
                "sample_data": sample_data
            }
        
        conn.close()
        
        return {
            "database_info": db_info,
            "total_tables": len(schema_info),
            "total_rows": total_rows,
            "tables": schema_info,
            "file_size_bytes": Path(db_path).stat().st_size,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "analysis_timestamp": datetime.now().isoformat()
        }

def main():
    """Main analysis entry point."""
    print("🔍 Agent Hive SQLite Database Analysis")
    print("=" * 50)
    
    # Find all .db files in current directory
    db_files = list(Path('.').glob('*.db'))
    
    if not db_files:
        print("❌ No SQLite database files found in current directory")
        return
    
    print(f"📊 Found {len(db_files)} database files")
    
    analysis = {
        "analysis_metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_databases": len(db_files),
            "databases_analyzed": 0,
            "databases_with_errors": 0
        },
        "databases": {}
    }
    
    for db_file in db_files:
        print(f"\n🔎 Analyzing {db_file}...")
        
        try:
            db_analysis = analyze_database(str(db_file))
            analysis["databases"][str(db_file)] = db_analysis
            
            if "error" in db_analysis:
                analysis["analysis_metadata"]["databases_with_errors"] += 1
                print(f"  ❌ Error: {db_analysis['error']}")
            else:
                analysis["analysis_metadata"]["databases_analyzed"] += 1
                print(f"  ✅ {db_analysis['total_tables']} tables, {db_analysis['total_rows']} total rows")
                
        except Exception as e:
            print(f"  ❌ Critical error analyzing {db_file}: {e}")
            analysis["databases"][str(db_file)] = {
                "critical_error": str(e),
                "analysis_timestamp": datetime.now().isoformat()
            }
            analysis["analysis_metadata"]["databases_with_errors"] += 1
    
    # Save analysis results
    output_file = Path('scratchpad/sqlite_analysis.json')
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    
    # Generate summary report
    summary_file = Path('scratchpad/database_migration_summary.md')
    generate_summary_report(analysis, summary_file)
    
    print(f"\n✅ Analysis complete!")
    print(f"📄 Detailed results: {output_file}")
    print(f"📋 Summary report: {summary_file}")
    print(f"📊 Analyzed: {analysis['analysis_metadata']['databases_analyzed']}/{len(db_files)} databases")
    
    if analysis['analysis_metadata']['databases_with_errors'] > 0:
        print(f"⚠️  {analysis['analysis_metadata']['databases_with_errors']} databases had errors")

def generate_summary_report(analysis: Dict[str, Any], output_file: Path):
    """Generate human-readable summary report."""
    
    total_tables = 0
    total_rows = 0
    total_size_mb = 0
    
    report_lines = [
        "# SQLite Database Analysis Summary",
        f"**Analysis Date**: {analysis['analysis_metadata']['timestamp']}",
        f"**Databases Found**: {analysis['analysis_metadata']['total_databases']}",
        f"**Databases Analyzed**: {analysis['analysis_metadata']['databases_analyzed']}",
        "",
        "## Database Overview",
        "",
        "| Database | Tables | Rows | Size (MB) | Status |",
        "|----------|--------|------|-----------|--------|"
    ]
    
    for db_name, db_data in analysis["databases"].items():
        if "error" in db_data or "critical_error" in db_data:
            status = "❌ Error"
            tables = 0
            rows = 0
            size_mb = 0
        else:
            status = "✅ Analyzed"
            tables = db_data["total_tables"]
            rows = db_data["total_rows"]
            size_mb = round(db_data["file_size_bytes"] / (1024 * 1024), 2)
            
            total_tables += tables
            total_rows += rows
            total_size_mb += size_mb
        
        report_lines.append(f"| {db_name} | {tables} | {rows:,} | {size_mb} | {status} |")
    
    report_lines.extend([
        "",
        "## Migration Planning Summary",
        "",
        f"- **Total Tables to Migrate**: {total_tables}",
        f"- **Total Rows to Migrate**: {total_rows:,}",
        f"- **Total Data Size**: {total_size_mb:.2f} MB",
        "",
        "## Next Steps",
        "",
        "1. **Schema Consolidation**: Design unified PostgreSQL schema",
        "2. **Data Mapping**: Create table mapping strategy", 
        "3. **Migration Scripts**: Develop data migration procedures",
        "4. **Validation**: Create data integrity validation tests",
        "",
        "## Critical Considerations",
        "",
        "- **Performance Impact**: Migration may take significant time for large datasets",
        "- **Data Integrity**: Ensure foreign key relationships are preserved",
        "- **Backup Strategy**: Create full backup before migration",
        "- **Rollback Plan**: Maintain SQLite files until migration validated",
        "",
        f"*Report generated by Agent Hive Database Migration Agent*"
    ])
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(report_lines))

if __name__ == "__main__":
    main()