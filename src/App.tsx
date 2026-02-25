import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import ChatPage from "./pages/ChatPage";
import Sidebar from "./components/Sidebar";
import LangQuestion from "./components/LangQuestion";

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen">
        <Sidebar />
        <div className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Home />} />
            {/* <Route path="/question" element={<LangQuestion />} /> */}
            <Route path="/chat/:session_id" element={<LangQuestion />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

// import { useState } from "react";
// import reactLogo from "./assets/react.svg";
// import viteLogo from "/vite.svg";
// // import "./App.css";
// import Upload from "./components/Upload";
// import UploadAndQueryStream from "./components/UploadAndQueryStream";
// import AskQuestion from "./components/AskQuestion";
// import UploadQuery from "./components/UploadQuery";
// // import UploadQuestion from "./components/UploadQuestion";
// import UploadOnly from "./components/UploadOnly";
// import UploadQuestion from "./components/UploadAndQuestion";
// import Question from "./components/Question";
// import StreamQuestion from "./components/StreamQuestion";
// import LangQuestion from "./components/LangQuestion";
// import LangUpload from "./components/LangUpload";

// function App() {
//   return (
//     <>
//       {/* <UploadQuery /> */}
//       {/* <UploadAndQueryStream /> */}
//       {/* <UploadOnly />
//       <Question /> */}

//       <LangQuestion />
//       {/* <StreamQuestion /> */}
//       {/* <UploadQuestion /> */}
//     </>
//   );
// }

// export default App;
