import styles from "./Dashboard.module.css";

export function Dashboard() {
  return (
    <div className={styles.dashboard}>
      <h1 className={styles.title}>Dashboard</h1>
      <p className={styles.subtitle}>Welcome to Repo Intelligence OS</p>
    </div>
  );
}
