import { describe, expect, it } from "vitest";
import { fakeCodec, pdfFile, photoFile } from "../../testing/attachments";
import { FileRejected, MAX_BYTES, MAX_SIDE_PX, prepareFile } from "./prepareFile";

describe("préparation d'un fichier avant envoi (RG-T26)", () => {
  it("photo : réduite à 1600 px en JPEG, nom de fichier propre", async () => {
    const codec = fakeCodec();
    const prepared = await prepareFile(photoFile(), codec);
    expect(codec.calls).toEqual([MAX_SIDE_PX]);
    expect(prepared.blob.type).toBe("image/jpeg");
    expect(prepared.fileName).toBe("IMG_0001.jpg");
  });

  it("PDF : envoyé tel quel jusqu'à 5 Mo, refusé au-delà", async () => {
    const codec = fakeCodec();
    const pdf = pdfFile();
    const prepared = await prepareFile(pdf, codec);
    expect(prepared.blob).toBe(pdf);
    expect(prepared.fileName).toBe("CNI-recto.pdf");
    expect(codec.calls).toEqual([]);
    const heavy = new File([new Uint8Array(MAX_BYTES + 1)], "gros.pdf", {
      type: "application/pdf",
    });
    await expect(prepareFile(heavy, codec)).rejects.toThrow(FileRejected);
  });

  it("autre fichier, ou photo encore trop lourde après réduction : refus lisible", async () => {
    const text = new File(["x"], "note.txt", { type: "text/plain" });
    await expect(prepareFile(text, fakeCodec())).rejects.toThrow("Format refusé");
    await expect(prepareFile(photoFile(), fakeCodec(MAX_BYTES + 1))).rejects.toThrow("trop lourde");
  });
});
