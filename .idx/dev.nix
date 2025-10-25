
{ pkgs, ... }: {
  # The list of packages to be installed
  # in your environment.
  packages = [
    # PyQt6 requires qt6.full for runtime dependencies
    pkgs.qt6.full
    # Creates a Python environment with the specified packages
    (pkgs.python3.withPackages (ps: with ps; [
      pandas
      openpyxl
      reportlab
      python-dotenv
      pyqt6
      matplotlib
      seaborn
    ]))
  ];
}
