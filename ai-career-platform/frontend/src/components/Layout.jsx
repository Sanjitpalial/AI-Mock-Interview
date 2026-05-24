import Navbar from './Navbar'
import Footer from './Footer'

import './Layout.css'

export default function Layout({ children }) {
  return (
    <div className="layout">
      <Navbar />
      <main className="layout__main">{children}</main>
      <Footer />
    </div>
  )
}
