from flask import Flask, render_template, request, redirect, url_for, jsonify

from app.db_connector import get_connection
from app.optimization.sp_loader import get_stored_procedures, get_sp_definition, get_tables, get_table_columns, get_table_indexes, get_slow_sp, get_stored_procedures_all_databases
from app.optimization.sp_optimizer import optimize_stored_procedure, sanitize_sql
from app.optimization.sp_saver import rename_sp_name, save_optimized_sp, save_sql_to_file
from app.indexing.fragmentation_analyzer import generate_maintenance_sql, analyze_index_fragmentation_all
from app.indexing.index_ai import get_index_recommendation
from app.indexing.sql_executor import execute_sql_statements
# from app.indexing.recommendation_builder import generate_recommendation_procedure
from app.utils.utils import is_similar_sql, log_result, log_to_sql, extract_table_names_from_sql, get_existing_index_info, extract_table_names_from_sql_new
from app.utils.logger import log_action

from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv(override=True)


# print("DEBUG SQL_DATABASE:", os.environ.get("SQL_DATABASE"))


app = Flask(__name__)

@app.route("/")
def index():
    # db_name = os.getenv("SQL_DATABASE")
    # sps = get_stored_procedures_all_databases(connection)
    # sps = [sp for sp in sps if not sp['is_encrypted']]
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze_index():
    with get_connection() as connection:
        db_name = os.getenv("SQL_DATABASE")
        results = analyze_index_fragmentation_all(connection)
        results = [r for r in results if r["recommendation"] in ("REBUILD", "REORGANIZE")]
        
        maintenance_sql = generate_maintenance_sql(results)
        # execute_sql_statements(connection, maintenance_sql)
        
        filename = f"index_recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        save_sql_to_file(maintenance_sql, filename)

        # ← Ambil daftar SP (misalnya pakai fungsi get_stored_procedures)
        all_sps = get_stored_procedures_all_databases(connection)
        sps_for_ui = [
            {"database":sp["database"],"schema": sp["schema"], "name": sp["name"]}
            for sp in all_sps if not sp["is_encrypted"]
        ]

        return render_template(
            "index_result.html",
            index_result=results,
            maintenance_sql=maintenance_sql,
            sp_list=sps_for_ui,
            ai_ready=False
        )

@app.route("/analyze_ai", methods=["POST"])
def analyze_ai():
    with get_connection() as connection:
        try:
            db_name = os.getenv("SQL_DATABASE")
            data = request.get_json()
            selected_sp = data.get("selected_sp")  # Contoh: "Production.uspGetBillOfMaterials"

            if not selected_sp or "." not in selected_sp:
                return jsonify({"ai_suggestions": "-- SP is invalid or not selected."})


            database_name, schema, name = selected_sp.split(".")

            # Ambil isi SP
            try:
                sp_text = get_sp_definition(connection, database_name, schema, name)
            except Exception as e:
                print(f"[ERROR] Failed to retrieve SP contents {selected_sp}: {e}")
                return jsonify({"ai_suggestions": f"-- Failed to read SP: {selected_sp}"})

            table_names = extract_table_names_from_sql_new(sp_text, database_name)
            print("Extracted table names:", table_names)
            # table_names could look like ["Sales.dbo.Orders", "Inventory.dbo.Products"]

            table_info_lines = []
            for table in table_names:
                try:
                    parts = table.split(".")
                    if len(parts) == 3:
                        db, sch, tbl = parts
                    elif len(parts) == 2:
                        # assume current database if DB not specified
                        db = database_name
                        sch, tbl = parts
                    else:
                        continue  # skip if can't parse

                    cols = get_table_columns(connection, db, sch, tbl)
                    
                    # Get indexes for this table
                    indexes = get_table_indexes(connection, db, sch, tbl)
                    # print(indexes)

                    # Format index info
                    if indexes:
                        index_info = []
                        for idx in indexes:
                            col_type = "included" if idx.is_included_column else "key"
                            index_info.append(f"{idx.index_name} ({col_type}: {idx.column_name})")
                        index_str = " | Indexes: " + ", ".join(index_info)
                    else:
                        index_str = ""

                    # table_info_lines.append(f"{db}.{sch}.{tbl} ({', '.join(cols)})")
                    # Append final line with columns and indexes
                    table_info_lines.append(f"{db}.{sch}.{tbl} ({', '.join(cols)}){index_str}")
                except Exception as e:
                    print(f"[WARN] Could not load columns for {table}: {e}")

            table_info = "\n".join(table_info_lines)

            # Kirim ke AI
            ai_suggestions = get_index_recommendation(sp_text, table_info)

            if not ai_suggestions:
                ai_suggestions = "-- (No AI recommendations)"
            else:
                save_sql_to_file(ai_suggestions, "index_ai_recommendations.sql")

            return jsonify({"ai_suggestions": ai_suggestions})

        except Exception as e:
            print("❌ ERROR WHILE RUNNING /analyze_ai:")
            import traceback
            traceback.print_exc()
            return jsonify({"ai_suggestions": f"❌ Internal error: {str(e)}"}), 500


@app.route("/build_index_proc", methods=["POST"])
def build_index_proc():
    with get_connection() as connection:
        db_name = "TestDB"

        # Analisis fragmentasi terbaru
        frag_results = analyze_index_fragmentation_all(connection)
        frag_results = [r for r in frag_results if r["recommendation"] in ("REBUILD", "REORGANIZE")]
        frag_sql = generate_maintenance_sql(frag_results)


        # Baca AI suggestions jika tersedia
        ai_sql = ""
        try:
            with open("outputs/index_ai_recommendations.sql", "r", encoding="utf-8") as f:
                ai_sql = f.read().strip()
        except FileNotFoundError:
            print("❗ AI recommendation file not found. Skip AI index.")

        # Gabungkan SQL
        final_sql = frag_sql.strip()

        if ai_sql and request.form.get("ai_used") == "1":
            final_sql += "\n\n-- AI Suggestions --\n" + ai_sql
        
        
        # Siapkan SQL untuk membuat SP recommendation_index
        sp_sql = f"""
        USE [{db_name}];

        IF OBJECT_ID('dbo.recommendation_index', 'P') IS NOT NULL
            DROP PROCEDURE dbo.recommendation_index;

        EXEC('
        CREATE PROCEDURE dbo.recommendation_index
        AS
        BEGIN
            SET NOCOUNT ON;

            {final_sql.replace("'", "''")}
        END
        ');
        """

        if final_sql == "":
            db_name = os.getenv("SQL_DATABASE")
            results = analyze_index_fragmentation_all(connection)
            results = [r for r in results if r["recommendation"] in ("REBUILD", "REORGANIZE")]
            
            maintenance_sql = generate_maintenance_sql(results)
            # execute_sql_statements(connection, maintenance_sql)
            
            filename = f"index_recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            save_sql_to_file(maintenance_sql, filename)

            # ← Ambil daftar SP (misalnya pakai fungsi get_stored_procedures)
            all_sps = get_stored_procedures(connection, db_name)
            sps_for_ui = [
                {"schema": sp["schema"], "name": sp["name"]}
                for sp in all_sps if not sp["is_encrypted"]
            ]
            return render_template(
                "index_result.html",
                index_result=results,
                maintenance_sql=maintenance_sql,
                sp_list=sps_for_ui,
                ai_ready=False
            )


        try:
            save_optimized_sp(connection, sp_sql)
            # return "✅ Stored Procedure <code>recommendation_index</code> berhasil dibuat!"

            save_sql_to_file(sp_sql, "recommendation_index.sql")

            log_action(
                action="Index Optimization + AI Index Recommendation",
                sp_name="dbo.recommendation_index",
                status="success",
                details=f"Optimized version saved as dbo.recommendation_index"
            )

            return render_template("save_result_optimize.html", sp_sql=sp_sql)

        except Exception as e:
            print(f"❌ Failed to create SP: {e}")

            log_action(
                action="Index Optimization + AI Index Recommendation",
                sp_name="dbo.recommendation_index",
                status="error",
                details=str(e)
            )

            return f"❌ Failed to create SP: {str(e)}", 500

@app.route("/execute_recommendation_index", methods=["POST"])
def execute_recommendation_index():
    with get_connection() as connection:
        try:
            db_name = 'TestDB' #os.getenv("SQL_DATABASE")
            cursor = connection.cursor()
            cursor.execute(f"USE [{db_name}]; EXEC dbo.recommendation_index;")
            connection.commit()

            result_message = "✅ Stored Procedure executed successfully."
            return render_template("execution_result.html", result=result_message)

        except Exception as e:
            error_message = f"❌ Failed to run SP: {str(e)}"
            print("❌ Failed to run SP:", e)
            return render_template("execution_result.html", result=error_message), 500


@app.route("/optimize", methods=["GET"])
def optimize_page():
    with get_connection() as connection:
        db_name = os.getenv("SQL_DATABASE")
        # sps = get_stored_procedures(connection, db_name)
        sps = get_stored_procedures_all_databases(connection)
        sps = [sp for sp in sps if not sp["is_encrypted"]]
        return render_template("optimize.html", stored_procedures=sps, db_name=db_name)

@app.route("/optimize_sp", methods=["POST"])
def optimize():
    with get_connection() as connection:
        # db_name = os.getenv("SQL_DATABASE")
        sp_full = request.form.get("sp_name")

        if not sp_full or "." not in sp_full:
            return "❌ Invalid SP data. Please select SP from the list."

        database_name, schema, name = sp_full.split(".")

        sp_text = get_sp_definition(connection, database_name, schema, name)
        if not sp_text:
            return f"Failed to retrieve SP definition {schema}.{name}"

        # Extract table names used in the SP
        table_names = extract_table_names_from_sql_new(sp_text, database_name)
        # table_names could look like ["Sales.dbo.Orders", "Inventory.dbo.Products"]

        print(table_names)

        table_info_lines = []
        for table in table_names:
            try:
                parts = table.split(".")
                if len(parts) == 3:
                    db, sch, tbl = parts
                elif len(parts) == 2:
                    # assume current database if DB not specified
                    db = database_name
                    sch, tbl = parts
                else:
                    continue  # skip if can't parse

                cols = get_table_columns(connection, db, sch, tbl)
                
                # Get indexes for this table
                indexes = get_table_indexes(connection, db, sch, tbl)
                # print(indexes)

                # Format index info
                if indexes:
                    index_info = []
                    for idx in indexes:
                        col_type = "included" if idx.is_included_column else "key"
                        index_info.append(f"{idx.index_name} ({col_type}: {idx.column_name})")
                    index_str = " | Indexes: " + ", ".join(index_info)
                else:
                    index_str = ""

                # table_info_lines.append(f"{db}.{sch}.{tbl} ({', '.join(cols)})")
                # Append final line with columns and indexes
                table_info_lines.append(f"{db}.{sch}.{tbl} ({', '.join(cols)}){index_str}")
                
            except Exception as e:
                print(f"[WARN] Could not load columns for {table}: {e}")

        table_info = "\n".join(table_info_lines)

        
        optimized_sql = optimize_stored_procedure(sp_text, table_info)
        if not optimized_sql:
            return "❌ Optimization failed (AI did not respond)."

        optimized_sql = sanitize_sql(optimized_sql)
        optimized_sql = optimized_sql.replace("=== END SP_OPTIMIZED ===", "")
        # print("Optimized SQL:", optimized_sql)
        optimized_sql = optimized_sql.replace("=== SP_OPTIMIZED ===", "")

        similar, ratio = is_similar_sql(sp_text, optimized_sql)

        return render_template("result.html", original=sp_text, optimized=optimized_sql,
                            database_name = database_name,schema=schema, name=name, similarity=round(ratio * 100, 2),
                            similar=similar)

@app.route("/save", methods=["POST"])
def save():
    with get_connection() as connection:
        db_name = request.form.get("database_name")
        sql_text = request.form.get("sql")
        schema = request.form.get("schema")
        name = request.form.get("name")

        optimized_sql, new_name = rename_sp_name(sql_text)
        # print(optimized_sql)
        success = save_optimized_sp(connection, optimized_sql, overwrite=True, db_name=db_name)
        status = "success" if success else "fail"

        # log_to_sql(connection, name, status)
        
        log_action(
            action="Index Optimization + AI Index Recommendation",
            sp_name=new_name,
            status=status,
            details=f"Optimized version saved as {new_name}"
        )

        return render_template(
            "save_result.html",
            status=status,
            original_name=f"{schema}.{name}",
            new_sp_name=f"{schema}.{new_name}",
            db_name=db_name
        )

@app.route("/slow-sp")
def slow_sp():
    with get_connection() as connection:
        data = get_slow_sp(connection)
        return render_template("slow_sp.html", rows=data)


if __name__ == "__main__":
    app.run(debug=True)
