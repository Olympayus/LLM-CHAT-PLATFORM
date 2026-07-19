"""数据导出工具 — PDF / Excel

提供统一的数据导出接口，支持将查询结果导出为 PDF 或 Excel 格式。

使用方式:
    from app.utils.export import export_data
    pdf_bytes = await export_data(data, format="pdf")
    excel_bytes = await export_data(data, format="excel")

TODO: 实际 PDF/Excel 生成依赖 reportlab/openpyxl 库，
      当前实现返回 CSV 格式作为过渡方案。
"""

import csv
import io
import json


async def export_data(
    data: list[dict],
    export_format: str = "excel",
    filename: str = "export",
) -> bytes:
    """导出数据

    Args:
        data: 要导出的数据列表（字典列表）
        export_format: 导出格式，pdf 或 excel
        filename: 导出文件名（不含扩展名）

    Returns:
        导出的文件内容（字节）

    TODO: 实际 PDF/Excel 实现：
        - PDF: 使用 reportlab 库生成表格 PDF，每页表头+行
        - Excel: 使用 openpyxl 库生成 .xlsx 文件，自动列宽
        当前过渡方案统一返回 UTF-8 CSV。
    """
    if not data:
        return b""

    output = io.StringIO()
    if export_format == "excel":
        # 过渡方案：返回 CSV（可用 Excel 打开）
        writer = csv.writer(output)
        # 写入表头
        headers = list(data[0].keys())
        writer.writerow(headers)
        # 写入数据行
        for row in data:
            writer.writerow([str(row.get(h, "")) for h in headers])
    else:
        # 过渡方案：返回 JSON（PDF 后续用 reportlab 实现）
        output.write(json.dumps(data, ensure_ascii=False, indent=2))

    return output.getvalue().encode("utf-8")