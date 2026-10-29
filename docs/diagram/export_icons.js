// Exporte des pictogrammes génériques (Font Awesome, licence CC BY 4.0) en SVG
const React = require("react"); const R = require("react-dom/server"); const fa = require("react-icons/fa");
const names = ["FaDatabase","FaCodeBranch","FaFlask","FaCheckCircle","FaBoxOpen","FaServer","FaUsers","FaChartLine","FaBell","FaSyncAlt","FaShieldAlt","FaCogs","FaUserCheck","FaGitAlt","FaHdd","FaHistory","FaWaveSquare","FaTachometerAlt","FaFileInvoiceDollar","FaMobileAlt","FaLaptopCode","FaVial","FaDocker","FaRocket","FaUndo","FaClipboardCheck","FaSearch","FaArchive","FaBalanceScale","FaHandPaper","FaEyeSlash","FaLaptop","FaExclamationTriangle","FaClock","FaCalendarAlt","FaPlay","FaFilter","FaRandom","FaCube","FaTags","FaLock","FaUserTie"];
const out = {};
for (const n of names) out[n] = R.renderToStaticMarkup(React.createElement(fa[n], { size: "64", color: "#FFFFFF" }));
require("fs").writeFileSync("icons.json", JSON.stringify(out));
console.log(Object.keys(out).length, "icônes");
