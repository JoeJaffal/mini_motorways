namespace MotorwaysSim
{
    /// Identifies the simulator's gameplay, scoring and observation semantics. The headless host
    /// reports it as `simulatorVersion` on every reply and prints it for `--version`, so result caches
    /// never reuse results from a different simulator. Bump it (YYYY-MM-DD.N) with any change that can
    /// alter a game, a score or the meaning of an observation field; record each value in
    /// simulation/Docs/VERSIONS.md. Hosts built before this field existed report nothing.
    public static class SimulatorVersion
    {
        public const string Value="2026-11-10.f11";
    }
}
