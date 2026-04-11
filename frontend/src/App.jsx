import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import DashboardLayout from './layouts/DashboardLayout';

import Dashboard from './pages/Dashboard';
import Registration from './pages/Registration';
import TrainModel from './pages/TrainModel';
import Capture from './pages/Capture';
import Records from './pages/Records';
import Settings from './pages/Settings';
import Landing from './pages/Landing';
import Classes from './pages/Classes';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/landing" element={<Landing />} />
        
        <Route path="/" element={<DashboardLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="register" element={<Registration />} />
          <Route path="train" element={<TrainModel />} />
          <Route path="capture" element={<Capture />} />
          <Route path="records" element={<Records />} />
          <Route path="classes" element={<Classes />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
