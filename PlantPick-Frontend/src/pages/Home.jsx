import { useState } from "react";
import { identifyPlant } from "../api/identify.js";

function Home() {
  const [plantInfo, setPlantInfo] = useState("");
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(false);

  console.log("Rendering Home.jsx: Before input and button");

  const handleFileChange = (event) => {
    console.log("File selected:", event.target.files[0]);
    setImage(event.target.files[0]);
  };

  const handleUpload = async () => {
    if (!image) return alert("📸 กรุณาเลือกไฟล์รูปภาพ");

    setLoading(true);
    console.log("Uploading image...");
    const result = await identifyPlant(image);
    setLoading(false);

    if (result.plant_info) {
      setPlantInfo(result.plant_info);
    } else {
      alert(
        "❌ ไม่สามารถวิเคราะห์ภาพได้: " + (result.error || "ไม่ทราบสาเหตุ")
      );
    }
  };

  return (
    <div>
      <h2>🏡 หน้าหลักของ PlantPick</h2>
      <p>ค้นหาต้นไม้ที่คุณต้องการได้เลย!</p>
      {console.log("Rendering input and button")}
      <input type="file" accept="image/*" onChange={handleFileChange} />
      <button onClick={handleUpload} disabled={loading}>
        {loading ? "🔄 กำลังค้นหา..." : "🔍 ค้นหา"}
      </button>
      {plantInfo && <h3>🌿 ผลลัพธ์: {plantInfo}</h3>}
    </div>
  );
}

export default Home;
