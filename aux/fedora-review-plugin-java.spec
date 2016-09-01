Name:           fedora-review-plugin-java
Version:        4.6.2
Release:        0.git.%(date +%%Y%%m%%d.%%H%%M%%S)
Summary:        Java plugin for FedoraReview
License:        GPLv2+
URL:            https://github.com/msimacek/fedora-review-plugin-java
BuildArch:      noarch

Source0:        https://github.com/msimacek/%{name}/archive/%{name}-%{version}.tar.gz

Requires:       fedora-review

%description
This package provides a plugin for FedoraReview tool that allows
checking packages for conformance with Java packaging guidelines.

%prep
%setup -q

%build

%install
mkdir -p %{buildroot}%{_datadir}/fedora-review/plugins/
install -pm644 fedora-review/java_guidelines.py %{buildroot}%{_datadir}/fedora-review/plugins/

%files
%{_datadir}/fedora-review/plugins/java_guidelines.py*
%{!?_licensedir:%global license %%doc}
%license LICENSE

%changelog
