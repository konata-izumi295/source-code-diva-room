// @category DivaRoom
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.app.decompiler.*;
import java.io.*;
import java.util.*;
public class InspectReferences extends GhidraScript {
 public void run() throws Exception {
  String[] args=getScriptArgs();PrintWriter out=new PrintWriter(new File(args[0]),"UTF-8");
  Set<Function> functions=new LinkedHashSet<>();
  for(int i=1;i<args.length;i++) {
   boolean only=args[i].startsWith("only:");var addr=toAddr(only?args[i].substring(5):args[i]);Function target=getFunctionContaining(addr);if(target!=null)functions.add(target);
   if(only)continue;
   for(Reference r:getReferencesTo(addr)) {
    Function f=getFunctionContaining(r.getFromAddress());out.println("REF "+addr+" <- "+r.getFromAddress()+" "+r.getReferenceType());
    if(f!=null)functions.add(f);
   }
  }
  DecompInterface d=new DecompInterface();d.openProgram(currentProgram);
  for(Function f:functions) {
   out.println("\nFUNCTION "+f.getEntryPoint());
   for(Reference r:getReferencesTo(f.getEntryPoint()))out.println("CALLER "+r.getFromAddress()+" "+r.getReferenceType());
   var res=d.decompileFunction(f,25,monitor);if(res.decompileCompleted())out.println(res.getDecompiledFunction().getC());out.flush();
   if(args[1].startsWith("only:")){var instructions=currentProgram.getListing().getInstructions(f.getBody(),true);while(instructions.hasNext()){var ins=instructions.next();out.println("ASM "+ins.getAddress()+" "+ins);}}
  }
  d.dispose();out.close();
 }
}
