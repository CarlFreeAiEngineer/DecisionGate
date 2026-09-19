# Email-address correction

The reported error was a YES answer to “Does this look like an email address is embedded in the comment?” for “I wish people would stop emailing me spam”. The correct answer is NO. The exact correction is the first record in [email-address-correction.jsonl](email-address-correction.jsonl).

The file contains 36 training, 12 validation, and 12 calibration examples, balanced within each partition. YES means a literal or clearly disguised email address appears, even if quoted, obsolete, or accompanied by a request not to use it. Merely mentioning email, spam, a website, a social handle, or a postal address means NO. Examples are original synthetic material marked unreviewed; addresses use reserved example domains. They do not establish comprehensive email syntax validation.

Continue from `runs/v2-nli-expanded/best`, retaining all original data and `data/expansion-v2.jsonl`. Run ten epochs with learning rate 0.00001, batch size 16, seed 42, on the Mac GPU. Select the checkpoint by lowest combined validation log loss, then calibrate using the combined calibration partition. Do not use the separate email test for checkpoint or hyperparameter selection.

Compare the frozen candidate with the existing release on the independently authored email test and the existing 80-case general test. Also record the exact correction and the original 52-case test. A candidate must fix the reported example, improve email test accuracy, and avoid reducing accuracy on either general test before consideration as a replacement. Retain the current release and document regressions if this gate fails. This experiment does not automatically rebuild or replace every platform package.
