import pg from 'pg';
import 'dotenv/config';
import fs from 'fs';
import path from 'path';

const { Pool } = pg;

const pool = new Pool({
  host: process.env.PGHOST || '192.168.124.126',
  port: process.env.PGPORT || 5432,
  database: process.env.PGDATABASE || 'pinggu',
  user: process.env.PGUSER || 'postgres',
  password: process.env.PGPASSWORD || 'wk888'
});

async function exportEnums() {
  try {
    // 导出 business_type
    const btSql = `SELECT DISTINCT business_type as name FROM evaluation_records WHERE business_type IS NOT NULL ORDER BY business_type`;
    const btResult = await pool.query(btSql);
    const businessTypeEnum = btResult.rows.map((r, i) => ({
      code: `BT${String(i + 1).padStart(3, '0')}`,
      name: r.name,
      aliases: [r.name]
    }));

    // 导出 service_desc
    const sdSql = `SELECT DISTINCT service_desc_code, service_desc_name FROM evaluation_records WHERE service_desc_code IS NOT NULL ORDER BY service_desc_code`;
    const sdResult = await pool.query(sdSql);
    const serviceDescEnum = sdResult.rows.map(r => ({
      code: r.service_desc_code,
      name: r.service_desc_name,
      aliases: [r.service_desc_name]
    }));

    // 导出 service_type
    const stSql = `SELECT DISTINCT service_type_code, service_type_name FROM evaluation_records WHERE service_type_code IS NOT NULL ORDER BY service_type_code`;
    const stResult = await pool.query(stSql);
    const serviceTypeEnum = stResult.rows.map(r => ({
      code: r.service_type_code,
      name: r.service_type_name,
      aliases: [r.service_type_name]
    }));

    // 导出 equipment_name (从 service_desc_name 映射)
    const eqSql = `SELECT DISTINCT service_desc_code, service_desc_name FROM evaluation_records WHERE service_desc_code IS NOT NULL ORDER BY service_desc_code`;
    const eqResult = await pool.query(eqSql);
    const equipmentNameEnum = eqResult.rows.map((r, i) => ({
      code: `EQ${String(i + 1).padStart(3, '0')}`,
      name: r.service_desc_name,
      aliases: [r.service_desc_name]
    }));

    // 导出 unit
    const unitSql = `SELECT DISTINCT equipment_unit FROM evaluation_records WHERE equipment_unit IS NOT NULL ORDER BY equipment_unit`;
    const unitResult = await pool.query(unitSql);
    const unitEnum = unitResult.rows.map((r, i) => ({
      code: `UM${String(i + 1).padStart(4, '0')}`,
      name: r.equipment_unit,
      aliases: [r.equipment_unit]
    }));

    // 构建 business_type 推断映射
    const btInference = {};
    sdResult.rows.forEach(r => {
      // 根据常见关键词推断业务类型
      const electricalKeywords = ['电气', '电', '控制', '报警', '系统', '配电', '发电机', '变频器', 'PLC', 'CCTV', '火警', '监控', '通讯', '导航', '信号'];
      const isElectrical = electricalKeywords.some(k => r.service_desc_name.includes(k));
      btInference[r.service_desc_code] = isElectrical ? 'BT002' : 'BT001';
    });

    const enums = {
      service_desc_enum: serviceDescEnum,
      service_type_enum: serviceTypeEnum,
      business_type_enum: businessTypeEnum,
      equipment_name_enum: equipmentNameEnum,
      unit_enum: unitEnum,
      business_type_inference: btInference,
      model_patterns: [
        "[0-9]{1,2}[A-Z][0-9]{2}[A-Z]{1,3}(?:-[A-Z0-9\\.]+)?",
        "MAN\\\\s*B&W-[0-9A-Z\\\\-\\\\.]+",
        "CONSILIUM.*",
        "SG-.*",
        "AUTROSAFETY.*"
      ],
      split_keywords: [
        "also",
        "and also",
        "in addition",
        "另外",
        "此外",
        "同时",
        "另一个",
        "另外一个"
      ]
    };

    const outputPath = path.join(process.cwd(), 'references', 'r2-enums-db.json');
    fs.writeFileSync(outputPath, JSON.stringify(enums, null, 2), 'utf8');
    console.log(`✅ 枚举文件已导出到：${outputPath}`);
    console.log(`\n统计信息:`);
    console.log(`  - business_type: ${businessTypeEnum.length} 项`);
    console.log(`  - service_desc: ${serviceDescEnum.length} 项`);
    console.log(`  - service_type: ${serviceTypeEnum.length} 项`);
    console.log(`  - equipment_name: ${equipmentNameEnum.length} 项`);
    console.log(`  - unit: ${unitEnum.length} 项`);

  } catch (err) {
    console.error('Error:', err.message);
  } finally {
    await pool.end();
  }
}

exportEnums();
