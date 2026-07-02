import { Outlet } from "react-router-dom";
import styles from "./RootLayout.module.css";

export function RootLayout() {
  return (
    <div className={styles.root}>
      <main className={styles.content}>
        <Outlet />
      </main>
    </div>
  );
}
