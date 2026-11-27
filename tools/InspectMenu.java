// Read-only export of menu strings, references, and candidate decompilations.
// @category DivaRoom
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.app.decompiler.*;
import java.io.*;
import java.util.*;

public class InspectMenu extends GhidraScript {
    public void run() throws Exception {
        PrintWriter out = new PrintWriter(new File(getScriptArgs()[0]), "UTF-8");
        out.println("Executable: " + currentProgram.getExecutablePath());
        out.println("SHA256: " + currentProgram.getExecutableSHA256());
        Set<Function> functions = new LinkedHashSet<>();
        if (getScriptArgs().length > 3) {
            for (int i = 3; i < getScriptArgs().length; i++) {
                Function f = getFunctionAt(toAddr(getScriptArgs()[i]));
                if (f == null) f = getFunctionContaining(toAddr(getScriptArgs()[i]));
                if (f != null) functions.add(f);
            }
        }
        DataIterator data = currentProgram.getListing().getDefinedData(true);
        while (data.hasNext() && !monitor.isCancelled()) {
            Data d = data.next();
            if (!d.hasStringValue()) continue;
            String value = String.valueOf(d.getValue());
            if (!(value.contains("nsw_menu_") || value.contains("nswgam_menu"))) continue;
            out.println("STRING " + d.getAddress() + " " + value);
            for (Reference ref : getReferencesTo(d.getAddress())) {
                Function f = getFunctionContaining(ref.getFromAddress());
                out.println("  REF " + ref.getFromAddress() + " function=" + (f == null ? "none" : f.getName()+"@"+f.getEntryPoint()));
                if (f != null) functions.add(f);
            }
        }
        if (getScriptArgs().length >= 3) {
            FunctionIterator near = currentProgram.getFunctionManager().getFunctions(toAddr(getScriptArgs()[1]), true);
            while (near.hasNext()) {
                Function f = near.next();
                if (f.getEntryPoint().compareTo(toAddr(getScriptArgs()[2])) > 0) break;
                functions.add(f);
            }
        }
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        for (Function f : functions) {
            out.println("\nFUNCTION " + f.getEntryPoint() + " " + f.getName());
            for (Reference ref : getReferencesTo(f.getEntryPoint()))
                out.println("CALLER " + ref.getFromAddress() + " " + ref.getReferenceType());
            DecompileResults result = decomp.decompileFunction(f, 20, monitor);
            if (result.decompileCompleted()) out.println(result.getDecompiledFunction().getC());
            else out.println(result.getErrorMessage());
            if (getScriptArgs().length > 3) {
                InstructionIterator instructions = currentProgram.getListing().getInstructions(f.getBody(), true);
                while (instructions.hasNext()) {
                    Instruction ins = instructions.next();
                    out.println("ASM " + ins.getAddress() + " " + ins);
                }
            }
            out.flush();
        }
        decomp.dispose();
        out.close();
        println("Exported " + functions.size() + " candidate functions.");
    }
}
