using System.Text;

namespace DecisionGate;

/// <summary>Optional descriptions of what counts as yes and what counts as no.</summary>
public sealed record Criteria(string Yes, string No);

/// <summary>One ranked option from <see cref="Decisions.ChooseP"/>.</summary>
public readonly record struct Choice(int Index, double P);

/// <summary>A native failure. Never returned as a false decision.</summary>
public sealed class DecisionGateException : Exception
{
    public int StatusCode { get; }
    internal DecisionGateException(int status, string message) : base(message) { StatusCode = status; }
}

/// <summary>Where the native bundle (library, model, tokenizer, manifest) lives.</summary>
public static class Bundle
{
    /// <summary>Set before the first call to choose the bundle directory explicitly.</summary>
    public static string? Directory { get; set; }

    internal static IEnumerable<string> Candidates()
    {
        if (Directory is not null) yield return Directory;
        var env = Environment.GetEnvironmentVariable("DECISIONGATE_BUNDLE");
        if (!string.IsNullOrEmpty(env)) yield return env;
        yield return Path.Combine(AppContext.BaseDirectory, "decisiongate");
        yield return AppContext.BaseDirectory;
    }
}

/// <summary>
/// Yes/no and multiple-choice decisions about text. The first call loads the
/// bundle and is slow; later calls reuse it. Calls are safe from any thread and
/// run one at a time. Errors throw; they are never disguised as "no".
/// </summary>
public static unsafe class Decisions
{
    /// <summary>Probability that the answer is yes, from 0 to 1.</summary>
    public static double IsYesP(string content, string question, Criteria? criteria = null)
    {
        var c = Utf8(content); var q = Utf8(question);
        var (cy, cn) = CriteriaBytes(criteria);
        fixed (byte* pc = c, pq = q, py = cy, pn = cn)
        {
            var crit = MakeCriteria(criteria, py, cy, pn, cn);
            int status = Native.IsYesP(pc, (nuint)c.Length, pq, (nuint)q.Length, criteria is null ? null : &crit, out double p);
            Check(status);
            return p;
        }
    }

    /// <summary>True when the probability of yes is at least <paramref name="threshold"/> (default 0.5).</summary>
    public static bool IsYes(string content, string question, Criteria? criteria = null, double threshold = 0.5)
    {
        CheckThreshold(threshold);
        var c = Utf8(content); var q = Utf8(question);
        var (cy, cn) = CriteriaBytes(criteria);
        fixed (byte* pc = c, pq = q, py = cy, pn = cn)
        {
            var crit = MakeCriteria(criteria, py, cy, pn, cn);
            int status = Native.IsYesAtThreshold(pc, (nuint)c.Length, pq, (nuint)q.Length, criteria is null ? null : &crit, threshold, out byte yes);
            Check(status);
            return yes == 1;
        }
    }

    /// <summary>Every option ranked best first; probabilities sum to one.</summary>
    public static IReadOnlyList<Choice> ChooseP(string content, string question, IReadOnlyList<string> options, Criteria? criteria = null)
    {
        if (options.Count < 2) throw new ArgumentException("at least two options are required", nameof(options));
        var c = Utf8(content); var q = Utf8(question);
        var (cy, cn) = CriteriaBytes(criteria);
        var optionBytes = options.Select(Utf8).ToArray();
        var handles = new System.Runtime.InteropServices.GCHandle[optionBytes.Length];
        var pointers = new byte*[optionBytes.Length];
        var lengths = new nuint[optionBytes.Length];
        var indexes = new int[optionBytes.Length];
        var probabilities = new double[optionBytes.Length];
        try
        {
            for (int i = 0; i < optionBytes.Length; i++)
            {
                handles[i] = System.Runtime.InteropServices.GCHandle.Alloc(optionBytes[i], System.Runtime.InteropServices.GCHandleType.Pinned);
                pointers[i] = (byte*)handles[i].AddrOfPinnedObject();
                lengths[i] = (nuint)optionBytes[i].Length;
            }
            fixed (byte* pc = c, pq = q, py = cy, pn = cn)
            fixed (byte** po = pointers)
            fixed (nuint* pl = lengths)
            fixed (int* pi = indexes)
            fixed (double* pp = probabilities)
            {
                var crit = MakeCriteria(criteria, py, cy, pn, cn);
                int status = Native.ChooseP(pc, (nuint)c.Length, pq, (nuint)q.Length, po, pl, (nuint)optionBytes.Length, criteria is null ? null : &crit, pi, pp);
                Check(status);
            }
        }
        finally
        {
            foreach (var h in handles) if (h.IsAllocated) h.Free();
        }
        var result = new Choice[optionBytes.Length];
        for (int i = 0; i < result.Length; i++) result[i] = new Choice(indexes[i], probabilities[i]);
        return result;
    }

    /// <summary>Index of the best option, or -1 when its probability is below <paramref name="threshold"/> (default 0, never -1).</summary>
    public static int Choose(string content, string question, IReadOnlyList<string> options, Criteria? criteria = null, double threshold = 0.0)
    {
        CheckThreshold(threshold);
        var best = ChooseP(content, question, options, criteria)[0];
        return best.P >= threshold ? best.Index : -1;
    }

    private static byte[] Utf8(string s) => Encoding.UTF8.GetBytes(s ?? throw new ArgumentNullException(nameof(s)));

    private static (byte[] yes, byte[] no) CriteriaBytes(Criteria? criteria) =>
        criteria is null ? (Array.Empty<byte>(), Array.Empty<byte>()) : (Utf8(criteria.Yes), Utf8(criteria.No));

    private static Native.Criteria MakeCriteria(Criteria? criteria, byte* py, byte[] cy, byte* pn, byte[] cn) =>
        criteria is null ? default : new Native.Criteria { Yes = py, YesBytes = (nuint)cy.Length, No = pn, NoBytes = (nuint)cn.Length };

    private static void CheckThreshold(double threshold)
    {
        if (double.IsNaN(threshold) || double.IsInfinity(threshold) || threshold < 0 || threshold > 1)
            throw new ArgumentOutOfRangeException(nameof(threshold), "threshold must be between 0 and 1 inclusive");
    }

    private static void Check(int status)
    {
        if (status != 0) throw new DecisionGateException(status, Native.LastErrorMessage());
    }
}
