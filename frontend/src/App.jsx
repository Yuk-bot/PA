import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Landing from '@/pages/Landing/Landing';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Landing page - root route */}
        <Route path="/" element={<Landing />} />

        
      </Routes>
    </BrowserRouter>
  );
}

export default App;