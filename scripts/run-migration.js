const { migrate } = require('./migrate');

// Run migration
migrate().then(() => {
  console.log('✅ Migration completed successfully!');
  process.exit(0);
}).catch((error) => {
  console.error('❌ Migration failed:', error);
  process.exit(1);
});
