import { HashRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { ResultsProvider } from './lib/ResultsContext'
import Overview from './pages/Overview'
import PromptInjection from './pages/PromptInjection'
import TokenReplay from './pages/TokenReplay'
import MerchantFraud from './pages/MerchantFraud'
import GraphFraud from './pages/GraphFraud'

export default function App() {
  return (
    <ResultsProvider>
      <HashRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Overview />} />
            <Route path="prompt-injection" element={<PromptInjection />} />
            <Route path="token-replay" element={<TokenReplay />} />
            <Route path="merchant-fraud" element={<MerchantFraud />} />
            <Route path="graph-fraud" element={<GraphFraud />} />
          </Route>
        </Routes>
      </HashRouter>
    </ResultsProvider>
  )
}
