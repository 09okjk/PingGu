import pg from 'pg';
import 'dotenv/config';

const { Pool } = pg;

const pool = new Pool({
  host: process.env.PGHOST || '192.168.124.126',
  port: process.env.PGPORT || 5432,
  database: process.env.PGDATABASE || 'pinggu',
  user: process.env.PGUSER || 'postgres',
  password: process.env.PGPASSWORD || 'wk888'
});

async function checkEnums() {
  try {
    // 检查 business_type
    const btSql = `SELECT DISTINCT business_type FROM evaluation_records ORDER BY business_type`;
    const btResult = await pool.query(btSql);
    console.log('=== business_type (业务归口) ===');
    console.log(btResult.rows.map(r => r.business_type));
    
    // 检查 service_desc_code
    const sdSql = `SELECT DISTINCT service_desc_code, service_desc_name FROM evaluation_records ORDER BY service_desc_code`;
    const sdResult = await pool.query(sdSql);
    console.log('\n=== service_desc_code (服务描述) ===');
    sdResult.rows.forEach(r => console.log(`${r.service_desc_code}: ${r.service_desc_name}`));
    
    // 检查 service_type_code
    const stSql = `SELECT DISTINCT service_type_code, service_type_name FROM evaluation_records ORDER BY service_type_code`;
    const stResult = await pool.query(stSql);
    console.log('\n=== service_type_code (服务类型) ===');
    stResult.rows.forEach(r => console.log(`${r.service_type_code}: ${r.service_type_name}`));
    
    // 检查是否有电气相关的记录
    const electricalSql = `SELECT service_desc_code, service_desc_name, COUNT(*) as cnt FROM evaluation_records WHERE business_type = '电气' OR service_desc_name LIKE '%电气%' OR service_desc_name LIKE '%消防%' GROUP BY service_desc_code, service_desc_name ORDER BY cnt DESC`;
    const elecResult = await pool.query(electricalSql);
    console.log('\n=== 电气/消防相关记录 ===');
    elecResult.rows.forEach(r => console.log(`${r.service_desc_code}: ${r.service_desc_name} (${r.cnt}条)`));
    
  } catch (err) {
    console.error('Error:', err.message);
  } finally {
    await pool.end();
  }
}

checkEnums();
